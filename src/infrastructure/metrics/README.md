# Metrics Tracking System v2.0

Complete redesign of the metrics tracking system with focus on comparative analysis and reliability.

## Features

✅ **Comprehensive Tracking**
- Token usage and costs (accurate pricing for all major LLMs)
- Agent execution metrics (duration, retries, success/failure)
- Pipeline tracking (all attempts, queue time, failed jobs)
- Tool usage statistics (call counts, durations, errors)
- Code metrics (files changed, lines added/deleted, test coverage)
- Debugging cycles (errors, attempts, resolution)

✅ **Reliability**
- Atomic writes (no data loss on crashes)
- Try/finally protection
- Automatic crash recovery
- State persistence

✅ **Comparative Analysis**
- Compare LLM models (which performs better?)
- Compare temperature settings
- Compare configurations (retries, coverage thresholds)
- Cost efficiency analysis
- Performance trends over time

✅ **Fully Tested**
- 26 comprehensive tests
- All functions validated
- Integration tests included

---

## Quick Start

### Basic Usage

```python
from src.infrastructure.metrics import MetricsCollector, MetricsStorage
from src.infrastructure.metrics.models import (
    AgentType, Status, SystemConfig, LLMConfig, CodeMetrics
)

# 1. Create configuration
config = SystemConfig(
    llm=LLMConfig(
        provider="deepseek",
        model="deepseek-chat",
        temperature=0.7
    ),
    max_retries=3,
    min_coverage_percent=70.0
)

# 2. Initialize collector and storage
collector = MetricsCollector(
    run_id="run_20251003_150000_project_171",
    project_id="171",
    config=config
)
storage = MetricsStorage()

# 3. Track an issue
collector.start_issue(issue_id=3)

# 4. Track agent execution
collector.start_agent(AgentType.CODING, issue_id=3)

# Track tool calls
call_id = collector.start_tool_call("create_branch")
# ... do work ...
collector.end_tool_call(call_id, success=True)

# Record token usage
token_usage = collector.record_token_usage(
    input_tokens=1500,
    output_tokens=800,
    model="deepseek-chat"
)

# Finalize agent
collector.finalize_agent(success=True, token_usage=token_usage)

# 5. Track pipeline
collector.record_pipeline(
    pipeline_id="12345",
    commit_sha="abc123",
    status="success",
    triggered_by="testing",
    execution_time_seconds=125.5
)

# 6. Finalize issue
code_metrics = CodeMetrics(
    files_created=3,
    files_modified=5,
    lines_added=250,
    test_coverage_percent=85.0
)
collector.finalize_issue(3, Status.COMPLETED, code_metrics=code_metrics)

# 7. Save everything
storage.save_issue_metrics(collector.run_metrics.run_id,
                           collector.get_issue_metrics(3))
storage.export_issue_to_csv(collector.run_metrics.run_id,
                            collector.get_issue_metrics(3))

# 8. Finalize run
run = collector.finalize_run(Status.COMPLETED)
storage.save_run_final(run)
storage.export_run_to_csv(run)
```

### Using Context Managers

```python
from src.infrastructure.metrics import MetricsContext

context = MetricsContext(collector)

# Auto-tracking with context managers
with context.track_issue(issue_id=3):
    # Track agent
    with context.track_agent(AgentType.CODING, issue_id=3):
        # Track tool calls
        with context.track_tool_call("create_file"):
            # Do work
            pass
```

---

## Integration with Supervisor

### Step 1: Initialize Metrics

```python
# In supervisor.__init__
from src.infrastructure.metrics import MetricsCollector, MetricsStorage
from src.infrastructure.metrics.models import SystemConfig, LLMConfig

# Create config from supervisor settings
config = SystemConfig(
    llm=LLMConfig(
        provider=os.getenv('LLM_PROVIDER', 'deepseek'),
        model=os.getenv('LLM_MODEL', 'deepseek-chat'),
        temperature=float(os.getenv('LLM_TEMPERATURE', '0.7'))
    ),
    max_retries=self.issue_manager.max_retries,
    min_coverage_percent=self.min_coverage,
    execution_mode=mode
)

# Initialize metrics
self.metrics_collector = MetricsCollector(
    run_id=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_project_{project_id}",
    project_id=project_id,
    config=config
)
self.metrics_storage = MetricsStorage()
```

### Step 2: Track Issue Implementation

```python
# In supervisor.implement_issue
async def implement_issue(self, issue: Dict) -> bool:
    issue_id = issue.get("iid")

    # Start tracking
    self.metrics_collector.start_issue(issue_id)

    try:
        # Coding phase
        self.metrics_collector.start_agent(AgentType.CODING, issue_id)

        # Track tool calls in agent executor
        # ... agent work ...

        token_usage = self.metrics_collector.record_token_usage(
            input_tokens=agent_response.usage.input_tokens,
            output_tokens=agent_response.usage.output_tokens,
            model=self.config.llm.model
        )

        self.metrics_collector.finalize_agent(
            success=True,
            token_usage=token_usage
        )

        # Track pipeline
        pipeline = await self.mcp.get_latest_pipeline(branch)
        self.metrics_collector.record_pipeline(
            pipeline_id=pipeline['id'],
            commit_sha=pipeline['sha'],
            status=pipeline['status'],
            triggered_by="coding"
        )

        # ... continue with other agents ...

        # Finalize issue
        code_metrics = await self._collect_code_metrics(branch)
        self.metrics_collector.finalize_issue(
            issue_id,
            Status.COMPLETED,
            code_metrics=code_metrics
        )

        # Save immediately (don't wait for run end)
        issue_metrics = self.metrics_collector.get_issue_metrics(issue_id)
        self.metrics_storage.save_issue_metrics(
            self.metrics_collector.run_metrics.run_id,
            issue_metrics
        )
        self.metrics_storage.export_issue_to_csv(
            self.metrics_collector.run_metrics.run_id,
            issue_metrics
        )

        return True

    except Exception as e:
        # Track error
        self.metrics_collector.record_error(
            error_type=type(e).__name__,
            error_message=str(e),
            severity="error"
        )

        self.metrics_collector.finalize_issue(issue_id, Status.FAILED)

        # Save even on failure
        issue_metrics = self.metrics_collector.get_issue_metrics(issue_id)
        self.metrics_storage.save_issue_metrics(
            self.metrics_collector.run_metrics.run_id,
            issue_metrics
        )

        return False
```

### Step 3: Ensure Finalization

```python
# In supervisor.execute - use try/finally
async def execute(self, mode: str = "implement"):
    try:
        # ... all work ...

    finally:
        # ALWAYS finalize, even on crashes
        run = self.metrics_collector.finalize_run(
            Status.COMPLETED if success else Status.FAILED
        )

        # Save final report
        self.metrics_storage.save_run_final(run)
        self.metrics_storage.export_run_to_csv(run)

        print(f"[METRICS] Saved to: logs/runs/{run.run_id}/")
```

---

## Comparative Analysis

### Compare LLM Models

```python
from src.infrastructure.metrics.analyzer import MetricsAnalyzer

analyzer = MetricsAnalyzer()

# Compare models
comparison = analyzer.compare_llm_models()

for model, stats in comparison.items():
    print(f"{model}:")
    print(f"  Success Rate: {stats['avg_success_rate']:.2f}%")
    print(f"  Avg Cost: ${stats['avg_cost']:.4f}")
    print(f"  Total Issues: {stats['total_issues_processed']}")
```

### Find Best Configuration

```python
best_config = analyzer.find_best_configuration()

print("Best Configuration:")
print(f"  Run ID: {best_config['best_run']['run_id']}")
print(f"  Model: {best_config['best_run']['config']['llm_model']}")
print(f"  Temperature: {best_config['best_run']['config']['llm_temperature']}")
print(f"  Score: {best_config['best_run']['score']:.2f}/100")
```

### Generate Full Report

```python
report = analyzer.generate_comparison_report(
    output_file=Path("logs/analysis_report.txt")
)
print(report)
```

---

## Cost Calculation

Accurate pricing for all major LLM providers (as of Oct 2025):

```python
# Pricing per 1M tokens
PRICING = {
    'deepseek-chat': {'input': $0.14, 'output': $0.28},
    'deepseek-coder': {'input': $0.14, 'output': $0.28},
    'gpt-4': {'input': $30.00, 'output': $60.00},
    'gpt-4-turbo': {'input': $10.00, 'output': $30.00},
    'gpt-3.5-turbo': {'input': $0.50, 'output': $1.50},
    'claude-3-opus': {'input': $15.00, 'output': $75.00},
    'claude-3-sonnet': {'input': $3.00, 'output': $15.00},
    'claude-3-haiku': {'input': $0.25, 'output': $1.25}
}
```

---

## Data Storage

### JSON Storage (Detailed)

```
logs/runs/
└── run_YYYYMMDD_HHMMSS_project_ID/
    ├── metadata.json              # Incremental updates
    ├── final_report.json          # Complete final report
    └── issues/
        ├── issue_1_metrics.json   # Incremental
        └── issue_1_report.json    # Final
```

### CSV Storage (Excel Analysis)

```
logs/csv/
├── runs.csv               # Run-level metrics
├── issues.csv             # Issue-level metrics
├── agents.csv             # Agent execution details
├── pipelines.csv          # Pipeline attempts
├── tool_usage.csv         # Tool call statistics
├── debugging_cycles.csv   # Debugging/retry cycles
└── errors.csv             # All errors
```

---

## Testing

Run comprehensive test suite:

```bash
cd C:\Users\esaui\Desktop\PythonProjects\AgenticSys
python -m pytest tests/infrastructure/test_metrics.py -v
```

All 26 tests should pass:
- ✅ Data models
- ✅ Metrics collector
- ✅ Storage (atomic writes)
- ✅ Context managers
- ✅ Complete workflow integration

---

## Migration from Old System

### Old System (Broken)
```python
# Old - scattered, incomplete
print(f"[INFO] Starting...")
self.run_logger.add_issue(issue_id)
await ws_manager.send_agent_output("Coding", "Working", "info")
self.issue_tracker.start_agent("coding")
# ... metrics never finalized ...
```

### New System (Reliable)
```python
# New - clean, complete, guaranteed
self.metrics_collector.start_issue(issue_id)
self.metrics_collector.start_agent(AgentType.CODING, issue_id)

# ... work ...

try:
    # Work happens
    pass
finally:
    # ALWAYS finalized
    self.metrics_collector.finalize_agent(success=True)
    self.metrics_storage.save_issue_metrics(...)
```

---

## FAQ

**Q: Will I lose data if the system crashes?**
A: No. Atomic writes ensure no partial data. Incremental saves mean you only lose the current operation.

**Q: How do I compare different LLM models?**
A: Use `MetricsAnalyzer.compare_llm_models()` or `find_best_configuration()`.

**Q: Where are costs calculated?**
A: In `MetricsCollector.record_token_usage()` with accurate per-model pricing.

**Q: Can I customize which metrics to track?**
A: Yes, all models are extensible. Add fields to dataclasses in `models.py`.

**Q: How do I analyze trends over time?**
A: Use `MetricsAnalyzer.analyze_performance_trends()`.

**Q: Are CSV files populated now?**
A: Yes! Every issue finalization exports to CSV immediately.

---

## Next Steps

1. ✅ **Integrate with Supervisor** - Replace old RunLogger/IssueTracker
2. ✅ **Add to AgentExecutor** - Track token usage from LLM responses
3. ✅ **Track Code Metrics** - Use GitLab MCP to get git diffs
4. ⏳ **Add Grafana Dashboard** - Visualize metrics in real-time
5. ⏳ **Add Prometheus Export** - For production monitoring

---

## Support

For issues or questions, see:
- Tests: `tests/infrastructure/test_metrics.py`
- Examples: This README
- Analysis: `docs/logging_metrics_analysis.md`
