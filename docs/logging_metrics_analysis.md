# Logging & Metrics System - Current State Analysis

## Date: 2025-10-03
## Analysis of: AgenticSys logging and metrics implementation

---

## Executive Summary

**Status: 🔴 CRITICAL ISSUES FOUND**

The logging and metrics system has fundamental problems:
- ✅ Data IS being captured to JSON files
- ❌ CSV exports are EMPTY (never populated)
- ❌ Runs never finalize (stuck in "running" status)
- ❌ Missing critical metrics (tokens, costs, tool usage)
- ❌ LLM configuration not captured ("unknown")
- ❌ No data when system crashes/interrupts

---

## 1. Current Storage Structure

### What EXISTS:
```
logs/
├── csv/                          # ❌ EMPTY - Only headers, no data
│   ├── runs.csv
│   ├── issues.csv
│   ├── agents.csv
│   ├── pipelines.csv
│   ├── debugging_cycles.csv
│   ├── errors.csv
│   └── tool_usage.csv
│
└── runs/
    ├── run_20251003_162539_project_171_metadata.json  # ✅ Has data, but stuck at "running"
    ├── run_20251003_164002_project_171_metadata.json  # ✅ Has data, but stuck at "running"
    ├── run_20251003_181952_project_171/
    │   ├── _metadata.json                             # ✅ Has data
    │   └── issues/
    │       └── issue_3_metrics.json                    # ✅ Has data
    └── ... (5 more runs, all stuck at "running")
```

### What's MISSING:
```
logs/runs/
    └── run_XXXXX/
        ├── _final.json           # ❌ Never created (finalize_run() never called)
        └── issues/
            └── issue_X_report.json  # ❌ Never created (finalize_issue() never called)
```

---

## 2. Data Accuracy Issues

### Issue #1: Runs Never Finalize 🔴 CRITICAL

**Evidence:**
```json
// logs/runs/run_20251003_181952_project_171_metadata.json
{
  "run_id": "run_20251003_181952_project_171",
  "status": "running",  // ❌ Should be "completed" or "failed"
  "issues_processed": ["3"],
  "total_errors": 0,
  "total_successes": 0  // ❌ Should be 1 (issue #3 was implemented)
}
```

**Root Cause:**
- `supervisor.execute()` method is interrupted before completion
- WebSocket disconnections cause system crashes
- Finalization code at end of `execute()` never runs
- No try/finally block to ensure cleanup

**Impact:**
- ❌ No final reports generated
- ❌ CSV files never populated
- ❌ Can't calculate success rates
- ❌ Can't analyze run performance

**Solution:**
```python
async def execute(self, mode: str = "implement", specific_issue: str = None):
    try:
        # ... execution logic ...
    except Exception as e:
        logger.error("Execution failed", exc_info=e)
        raise
    finally:
        # ALWAYS finalize, even on crashes
        await self._finalize_run()
```

---

### Issue #2: CSV Exports Are Empty 🔴 CRITICAL

**Evidence:**
```bash
$ wc -l logs/csv/*.csv
   1 logs/csv/agents.csv      # Only header
   1 logs/csv/issues.csv      # Only header
   1 logs/csv/runs.csv        # Only header
```

**Root Cause:**
1. `csv_exporter.export_run()` is called at line 549 of supervisor.py
2. BUT it's after finalization code (line 531)
3. If finalization doesn't happen, CSV export doesn't happen
4. No intermediate exports during run

**Impact:**
- ❌ No Excel analysis possible
- ❌ Can't compare runs
- ❌ Can't track trends
- ❌ All CSV infrastructure is wasted

**Solution:**
```python
# Option A: Export incrementally
async def implement_issue(self, issue: Dict):
    # ... do work ...
    if result:
        # Export immediately, don't wait for run end
        self.csv_exporter.export_issue(self.run_logger.run_id, issue_data)

# Option B: Export on finalize with finally block
async def execute(self):
    try:
        # ... work ...
    finally:
        self._export_to_csv()  # Always export what we have
```

---

### Issue #3: LLM Configuration Not Captured 🟡 HIGH

**Evidence:**
```json
{
  "llm_configuration": {
    "provider": "unknown",  // ❌ Should be "deepseek", "openai", etc.
    "model": "unknown",     // ❌ Should be "deepseek-chat", etc.
    "temperature": 0.0      // ❌ Should be actual value
  }
}
```

**Root Cause:**
- RunLogger expects `config` dict with LLM settings
- Supervisor initializes with `llm_config` parameter
- But when called from Web GUI, it's not passed correctly

**Code Path:**
```python
# web_gui/backend/core/orchestrator.py:154
llm_config = {
    'provider': config.get('llm_provider', 'unknown'),  # ❌ Falls back to 'unknown'
    'model': config.get('llm_model', 'unknown'),
    'temperature': config.get('llm_temperature', 0.0)
}
self.supervisor = Supervisor(project_id, tech_stack, llm_config, mcp_log_callback)
```

**Impact:**
- ❌ Can't compare LLM performance
- ❌ Can't track costs per model
- ❌ Can't analyze which model is better

**Solution:**
```python
# Ensure config is always passed from GUI
config = {
    'llm_provider': os.getenv('LLM_PROVIDER', 'deepseek'),  # ✅ Get from env
    'llm_model': os.getenv('LLM_MODEL', 'deepseek-chat'),
    'llm_temperature': float(os.getenv('LLM_TEMPERATURE', '0.7'))
}
```

---

### Issue #4: Agent Metrics Incomplete 🟡 HIGH

**Evidence:**
```json
// issue_3_metrics.json
{
  "agent_metrics": {
    "coding": {
      "attempts": 3,
      "successes": 3,
      "duration": 722.19  // ✅ Captured
    },
    "review": {
      "attempts": 3,
      "successes": 0,      // ❌ Wrong! Review actually succeeded
      "failures": 3        // ❌ Incorrect data
    }
  },
  "pipeline_attempts": 0,    // ❌ Should be 3+ (pipelines ran multiple times)
  "debugging_cycles": 0,     // ❌ Should have debugging data
  "errors": 0                // ❌ There were errors (review "failed" 3 times)
}
```

**Root Cause:**
- `issue_tracker.start_agent()` and `end_agent()` are called correctly
- BUT review agent "succeeded" (merged MR) but metrics show "failed"
- Pipeline attempts not being recorded (no calls to `record_pipeline_attempt()`)
- Debugging cycles not being tracked (no calls to `start_debugging_cycle()`)

**Impact:**
- ❌ Incorrect success/failure counts
- ❌ Can't analyze retry patterns
- ❌ Can't identify bottlenecks
- ❌ Can't measure debugging effectiveness

**Solution:**
```python
# In AgentExecutor - track pipeline attempts
async def execute_coding_agent(self, issue, branch):
    # ... agent runs ...

    # Track pipeline
    pipeline_id = await self._get_latest_pipeline(branch)
    if pipeline_id and self.issue_tracker:
        status = await self._get_pipeline_status(pipeline_id)
        self.issue_tracker.record_pipeline_attempt(pipeline_id, status)

    return result

# Track debugging cycles when retrying
if not result and attempt < max_retries:
    self.issue_tracker.start_debugging_cycle("coding", "test_failure", error_msg)
    # ... retry ...
    self.issue_tracker.end_debugging_cycle(resolved=new_result)
```

---

## 3. Missing Metrics (Critical Gaps)

### A. Token Usage & Costs ❌ NOT CAPTURED

**What's Defined:**
```python
# CSV schema has columns for:
- total_tokens
- input_tokens
- output_tokens
- estimated_cost_usd
```

**What's Implemented:**
```python
# agent_executor.py has show_tokens parameter
show_tokens: bool = True  # Passed to agents
```

**What's Missing:**
```python
# ❌ No code to capture token usage from agents
# ❌ No code to calculate costs
# ❌ No storage of token metrics
```

**Impact:**
- ❌ Can't track costs per issue
- ❌ Can't compare model efficiency
- ❌ Can't budget for production
- ❌ Can't optimize for cost

**Required Implementation:**
```python
class AgentExecutor:
    async def execute_coding_agent(self, issue, branch):
        # Capture agent response with usage
        result = await run_coding_agent(...)

        # Extract usage from agent response
        if hasattr(result, 'usage'):
            usage = {
                'input_tokens': result.usage.input_tokens,
                'output_tokens': result.usage.output_tokens,
                'total_tokens': result.usage.total_tokens,
                'estimated_cost': self._calculate_cost(result.usage, model_name)
            }

            # Store in issue tracker
            if self.issue_tracker:
                self.issue_tracker.record_token_usage('coding', usage)

        return result

    def _calculate_cost(self, usage, model: str) -> float:
        # Cost calculation based on model pricing
        pricing = {
            'deepseek-chat': {'input': 0.14 / 1_000_000, 'output': 0.28 / 1_000_000},
            'gpt-4': {'input': 30.0 / 1_000_000, 'output': 60.0 / 1_000_000}
        }

        model_price = pricing.get(model, {'input': 0, 'output': 0})
        cost = (usage.input_tokens * model_price['input'] +
                usage.output_tokens * model_price['output'])
        return cost
```

---

### B. Tool Usage Statistics ❌ NOT CAPTURED

**What's Defined:**
```python
# CSV schema:
- tool_name
- call_count
- success_count
- failure_count
- avg_duration_ms
```

**What's Missing:**
- No tracking of which tools are called
- No tracking of tool success/failure
- No timing of tool execution

**Impact:**
- ❌ Can't identify slow tools
- ❌ Can't optimize tool usage
- ❌ Can't detect tool failures

**Required Implementation:**
```python
class ToolMonitor:
    def __init__(self):
        self.tool_stats = {}

    async def track_tool_call(self, tool_name: str, func, *args, **kwargs):
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = (time.time() - start) * 1000  # ms

            self._record_success(tool_name, duration)
            return result
        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_failure(tool_name, duration, str(e))
            raise

    def _record_success(self, tool_name, duration):
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = {
                'calls': 0, 'successes': 0, 'failures': 0,
                'total_duration': 0, 'errors': []
            }

        self.tool_stats[tool_name]['calls'] += 1
        self.tool_stats[tool_name]['successes'] += 1
        self.tool_stats[tool_name]['total_duration'] += duration
```

---

### C. Code Metrics ❌ NOT CAPTURED

**What's Defined:**
```python
# CSV schema:
- files_created
- files_modified
- lines_added
- lines_deleted
- commits
- test_coverage
```

**What's Missing:**
- All code metrics are 0/null
- No integration with git to track changes
- No coverage parsing

**Impact:**
- ❌ Can't measure code complexity
- ❌ Can't track test coverage trends
- ❌ Can't assess code quality

**Required Implementation:**
```python
class CodeMetricsCollector:
    async def collect_for_branch(self, branch: str) -> Dict:
        # Get diff stats from git
        diff_stats = await self._get_git_diff_stats(branch)

        # Parse coverage from pipeline artifacts
        coverage = await self._parse_coverage_report(branch)

        return {
            'files_created': diff_stats['files_created'],
            'files_modified': diff_stats['files_modified'],
            'lines_added': diff_stats['insertions'],
            'lines_deleted': diff_stats['deletions'],
            'commits': diff_stats['commit_count'],
            'test_coverage': coverage
        }

    async def _get_git_diff_stats(self, branch: str):
        # Use GitLab MCP tools
        commits = await mcp.get_branch_commits(branch)
        diffs = await mcp.get_branch_diff(branch, 'master')

        return {
            'files_created': len([f for f in diffs if f['new_file']]),
            'files_modified': len([f for f in diffs if not f['new_file']]),
            'insertions': sum(f['additions'] for f in diffs),
            'deletions': sum(f['deletions'] for f in diffs),
            'commit_count': len(commits)
        }
```

---

### D. Pipeline Metrics ❌ PARTIALLY CAPTURED

**Current State:**
```json
{
  "pipeline_attempts": 0,       // ❌ Not tracked
  "succeeded_pipelines": 0,     // ❌ Not tracked
  "failed_pipelines": 0         // ❌ Not tracked
}
```

**What's Missing:**
- Pipeline status not being recorded
- Job-level failures not tracked
- Queue/execution time not measured

**Required Implementation:**
```python
class PipelineMonitor:
    async def track_pipeline(self, branch: str, issue_id: int):
        # Get latest pipeline for branch
        pipeline = await mcp.get_latest_pipeline(branch)

        # Wait for completion and track
        final_status = await self._wait_for_pipeline(pipeline['id'])

        pipeline_data = {
            'pipeline_id': pipeline['id'],
            'status': final_status,
            'duration': pipeline['duration'],
            'failed_jobs': self._extract_failed_jobs(pipeline),
            'queue_time': pipeline['queued_duration'],
            'execution_time': pipeline['duration']
        }

        # Record in issue tracker
        if self.issue_tracker:
            self.issue_tracker.record_pipeline_attempt(
                pipeline['id'],
                final_status,
                pipeline['sha']
            )

        return pipeline_data
```

---

## 4. Data Consistency Issues

### Problem: Metrics Scattered Across Multiple Systems

**Current State:**
```python
# Business logic mixed with metrics:
print(f"[ISSUE #{issue_id}] Starting")                      # Console log
self.issue_tracker.start_agent("coding")                    # JSON metric
await ws_manager.send_agent_output("Coding", "Start", "info") # WebSocket
self.run_logger.add_issue(issue_id)                        # Run-level metric
```

**Issues:**
1. Easy to forget one of these calls
2. No atomic updates (partial failures possible)
3. Hard to maintain consistency
4. Duplication of data

**Example Inconsistency:**
```json
// From logs: Review agent "failed" 3 times
"review": {
  "attempts": 3,
  "failures": 3  // ❌ Incorrect
}

// From GitLab: MR was merged successfully
MR !1: merged at 18:42:18  // ✅ Actual truth
Issue #3: closed            // ✅ Actual truth
```

**Solution:** Unified event system (from redesign doc)
```python
# Single source of truth
events.emit("agent.completed", {
    "agent": "review",
    "issue_id": 3,
    "success": True,  # Single source of truth
    "mr_merged": True
})

# All systems subscribe
- logger subscribes → writes log
- issue_tracker subscribes → updates metrics
- ws_manager subscribes → sends GUI update
- csv_exporter subscribes → writes CSV
```

---

## 5. Performance & Scalability Issues

### Issue #1: Synchronous File Writes 🟡 MEDIUM

**Current Code:**
```python
def _save_metrics(self):
    """Called on every agent start/end"""
    metrics_file = self.logs_dir / f"issue_{self.issue_id}_metrics.json"
    with open(metrics_file, 'w') as f:  # ❌ Blocking I/O
        json.dump(current_data, f, indent=2)
```

**Problem:**
- File write on every metric update
- Blocks async execution
- Slows down agent execution

**Impact:**
- 🐌 Slower issue processing
- 💾 Excessive disk I/O
- 🔒 Blocks event loop

**Solution:**
```python
# Option A: Batch writes
class IssueTracker:
    def __init__(self):
        self.dirty = False
        self._save_task = None

    def _mark_dirty(self):
        self.dirty = True
        if not self._save_task:
            # Save every 5 seconds if dirty
            self._save_task = asyncio.create_task(self._periodic_save())

    async def _periodic_save(self):
        while self.dirty:
            await asyncio.sleep(5)
            if self.dirty:
                await self._async_save_metrics()
                self.dirty = False

# Option B: Write to queue, background thread writes
import queue
import threading

class AsyncFileWriter:
    def __init__(self):
        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self._worker)
        self.worker.start()

    def write(self, filepath, data):
        self.queue.put((filepath, data))

    def _worker(self):
        while True:
            filepath, data = self.queue.get()
            with open(filepath, 'w') as f:
                json.dump(data, f)
```

---

### Issue #2: No Log Rotation 🟡 MEDIUM

**Current State:**
```python
# Logs accumulate indefinitely
logs/runs/
    ├── run_20251003_162539_...  # Never deleted
    ├── run_20251003_164002_...
    ├── run_20251003_164323_...
    └── ... (grows forever)
```

**Impact:**
- 💾 Disk space grows unbounded
- 🐌 Slower file system operations
- 🗑️ Old logs clutter system

**Solution:**
```python
class LogRotation:
    def __init__(self, max_runs=100, max_age_days=30):
        self.max_runs = max_runs
        self.max_age_days = max_age_days

    async def rotate(self):
        # Delete old runs
        all_runs = sorted(Path('logs/runs').glob('run_*'))

        # Keep only last max_runs
        if len(all_runs) > self.max_runs:
            for old_run in all_runs[:-self.max_runs]:
                shutil.rmtree(old_run)

        # Delete runs older than max_age_days
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        for run_dir in all_runs:
            run_time = datetime.strptime(run_dir.name[4:19], '%Y%m%d_%H%M%S')
            if run_time < cutoff:
                shutil.rmtree(run_dir)
```

---

## 6. Recommended Improvements

### Priority 1: Fix Critical Issues (Week 1)

1. **Add try/finally to ensure finalization**
   ```python
   async def execute(self):
       try:
           # ... work ...
       finally:
           await self._finalize()  # Always runs
   ```

2. **Capture LLM configuration correctly**
   ```python
   # Get from environment or config
   llm_config = self._get_llm_config_from_env()
   ```

3. **Fix agent success/failure tracking**
   ```python
   # Use GitLab state as source of truth
   if mr_merged and issue_closed:
       success = True  # Regardless of retries
   ```

### Priority 2: Add Missing Metrics (Week 2)

4. **Implement token tracking**
   - Capture from agent responses
   - Calculate costs
   - Store in metrics

5. **Implement code metrics**
   - Parse git diffs
   - Extract coverage from artifacts
   - Track file changes

6. **Implement pipeline tracking**
   - Record all pipeline attempts
   - Track failed jobs
   - Measure queue/execution time

### Priority 3: Improve Architecture (Week 3)

7. **Implement unified logging** (see redesign doc)
8. **Add event-driven metrics** (pub/sub pattern)
9. **Add async file writes** (performance)
10. **Add log rotation** (disk management)

---

## 7. Metrics We SHOULD Capture (Comprehensive List)

### Run-Level Metrics ✅/❌
- ✅ Run ID, project ID, start/end time
- ✅ Execution mode (implement_all, single_issue, analyze)
- ❌ LLM configuration (currently "unknown")
- ✅ Total issues processed
- ❌ Total successes (currently 0, should count from finalized issues)
- ❌ Total errors (currently 0, not tracking properly)
- ❌ Total cost (not calculated)
- ❌ Total tokens (not captured)

### Issue-Level Metrics ✅/❌
- ✅ Issue ID, start/end time, duration
- ❌ Status (stuck at "in_progress", never finalized)
- ❌ Complexity score (always 0, not implemented)
- ✅ Agent attempts and durations
- ❌ Agent successes/failures (incorrect data)
- ❌ Pipeline attempts (always 0, not tracked)
- ❌ Debugging cycles (always 0, not tracked)
- ❌ Token usage (not captured)
- ❌ Cost (not calculated)
- ❌ Code metrics (all 0, not implemented)
- ❌ Test coverage (not captured)
- ❌ First-time-right (not calculated)

### Agent-Level Metrics ✅/❌
- ✅ Agent name, attempt number
- ✅ Start/end time, duration
- ❌ Success/failure (incorrect in some cases)
- ❌ Retries (always 0, not tracking)
- ❌ Tool calls (not tracked)
- ❌ Tokens used (not captured)
- ❌ Error messages (not stored)

### Pipeline-Level Metrics ❌ (NONE CAPTURED)
- ❌ Pipeline ID, commit SHA
- ❌ Triggered by (agent)
- ❌ Retry attempt number
- ❌ Start/end time, duration
- ❌ Status (success/failed)
- ❌ Failed jobs list
- ❌ Error type
- ❌ Queue time vs execution time

### Tool Usage Metrics ❌ (NONE CAPTURED)
- ❌ Tool name
- ❌ Call count
- ❌ Success count
- ❌ Failure count
- ❌ Average duration
- ❌ Total duration

### Code Metrics ❌ (NONE CAPTURED)
- ❌ Files created
- ❌ Files modified
- ❌ Lines added
- ❌ Lines deleted
- ❌ Number of commits
- ❌ Test coverage percentage

### Debugging Metrics ❌ (NONE CAPTURED)
- ❌ Error type (test_failure, build_error, lint_error)
- ❌ Error message
- ❌ Debugging attempts
- ❌ Resolved (yes/no)
- ❌ Resolution method
- ❌ Time to resolution

### Cost Metrics ❌ (NONE CAPTURED)
- ❌ Input tokens
- ❌ Output tokens
- ❌ Total tokens
- ❌ Estimated cost in USD
- ❌ Cost per issue
- ❌ Cost per agent
- ❌ Cost breakdown by model

---

## 8. Conclusion

### Summary of Findings:

**What Works:**
- ✅ JSON metadata files are created
- ✅ Issue metrics are tracked (partially)
- ✅ Basic agent timing works
- ✅ CSV schema is well-designed

**What's Broken:**
- 🔴 Runs never finalize (critical)
- 🔴 CSV files are empty (critical)
- 🔴 LLM config not captured (high)
- 🔴 Agent success/failure incorrect (high)
- 🔴 Pipeline metrics missing (high)
- 🔴 Token/cost tracking missing (high)
- 🔴 Code metrics missing (medium)
- 🔴 Tool usage missing (medium)

**Recommendation:**
Implement the unified logging system from `logging_redesign.md` while fixing the critical issues identified here. The new architecture will prevent many of these issues and make the system more maintainable.

**Next Steps:**
1. Fix finalization with try/finally ✅ Priority 1
2. Capture LLM configuration ✅ Priority 1
3. Add token/cost tracking ✅ Priority 2
4. Implement pipeline monitoring ✅ Priority 2
5. Deploy unified logging system ✅ Priority 3
