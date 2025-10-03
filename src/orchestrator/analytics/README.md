# Analytics & Metrics Tracking System

Comprehensive logging system for tracking all system runs, issues, agents, and pipelines.

## Overview

The analytics system provides detailed tracking of:
- **Run Configuration**: LLM provider, model, temperature for each system run
- **Issue Metrics**: Per-issue tracking of errors, pipelines, and debugging cycles
- **Agent Performance**: Attempts, successes, failures, and retries for each agent
- **Pipeline Tracking**: Every pipeline attempt with success/failure status
- **Debugging Cycles**: How many times agents had to rework code to fix issues

## Architecture

```
src/orchestrator/analytics/
├── run_logger.py       # Tracks overall run configuration
├── issue_tracker.py    # Detailed per-issue metrics
├── metrics.py          # Data classes for metrics
└── README.md          # This file
```

## Log Files Structure

```
logs/runs/
├── run_20241203_143022_project_168/
│   ├── run_20241203_143022_project_168_metadata.json  # Run config
│   ├── run_20241203_143022_project_168_final.json    # Final summary
│   └── issues/
│       ├── issue_123_metrics.json   # Real-time metrics
│       ├── issue_123_report.json    # Final report
│       ├── issue_124_metrics.json
│       └── issue_124_report.json
```

## Usage Example

### 1. Initialize Run Logger (in Supervisor)

```python
from src.orchestrator.analytics import RunLogger, IssueTracker

# At system start
config = {
    'llm_provider': 'deepseek',
    'llm_model': 'deepseek-chat',
    'llm_temperature': 0.0,
    'mode': 'implement_all'
}

run_logger = RunLogger(project_id='168', config=config)
```

### 2. Track Each Issue

```python
# When starting to process an issue
issue_tracker = IssueTracker(run_id=run_logger.run_id, issue_id=123)
run_logger.add_issue(issue_id=123)

# Track agent execution
issue_tracker.start_agent('coding')
# ... agent executes ...
issue_tracker.end_agent('coding', success=True)

# Track pipeline
issue_tracker.record_pipeline_attempt(
    pipeline_id='4259',
    status='failed',
    commit_sha='abc123'
)

# Track debugging cycle when pipeline fails
issue_tracker.start_debugging_cycle(
    agent='testing',
    error_type='test_failure',
    error_message='3 tests failed in UserServiceTest'
)
issue_tracker.record_debug_attempt()  # First fix attempt
issue_tracker.record_debug_attempt()  # Second fix attempt
issue_tracker.end_debugging_cycle(resolved=True)

# Another pipeline after fixes
issue_tracker.record_pipeline_attempt(
    pipeline_id='4260',
    status='success',
    commit_sha='def456'
)

# Finalize issue
issue_tracker.finalize_issue(status='completed')
```

### 3. Finalize Run

```python
# At system end
run_logger.finalize_run(status='completed')
```

## Tracked Metrics

### Run Level (`run_*_final.json`)
```json
{
  "run_id": "run_20241203_143022_project_168",
  "project_id": "168",
  "llm_configuration": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "temperature": 0.0
  },
  "duration_seconds": 1847.3,
  "issues_processed": [123, 124, 125],
  "total_successes": 2,
  "total_errors": 1,
  "success_rate": 66.67
}
```

### Issue Level (`issue_*_report.json`)
```json
{
  "issue_id": 123,
  "status": "completed",
  "duration_seconds": 523.2,

  "agent_metrics": {
    "coding": {
      "attempts": 1,
      "successes": 1,
      "failures": 0,
      "retries": 0,
      "duration": 45.3
    },
    "testing": {
      "attempts": 1,
      "successes": 1,
      "failures": 0,
      "retries": 2,
      "duration": 289.5
    },
    "review": {
      "attempts": 1,
      "successes": 1,
      "failures": 0,
      "retries": 0,
      "duration": 142.7
    }
  },

  "pipeline_attempts": 3,
  "succeeded_pipelines": 1,
  "failed_pipelines": 2,
  "pipeline_success_rate": 33.33,

  "total_errors": 2,
  "debugging_cycles": 1,
  "resolved_cycles": 1,
  "debugging_success_rate": 100.0,

  "debugging_details": [
    {
      "agent": "testing",
      "error_type": "test_failure",
      "attempts": 2,
      "resolved": true,
      "duration_seconds": 178.2
    }
  ],

  "pipeline_details": [
    {"pipeline_id": "4258", "status": "failed", "commit_sha": "abc123"},
    {"pipeline_id": "4259", "status": "failed", "commit_sha": "abc124"},
    {"pipeline_id": "4260", "status": "success", "commit_sha": "def456"}
  ]
}
```

## Key Insights from Metrics

### What You Can Analyze:

1. **LLM Impact**: Compare success rates across different models/temperatures
2. **Agent Performance**: Which agents need most retries?
3. **Pipeline Reliability**: How often do pipelines pass on first try?
4. **Debugging Efficiency**: How quickly are errors resolved?
5. **Issue Complexity**: Correlation between retries and issue difficulty

### Example Queries:

- "Which LLM model has highest success rate?"
- "What percentage of pipelines pass on first attempt?"
- "How many debugging cycles per issue on average?"
- "Which agent (coding/testing/review) causes most retries?"

## Integration Points

The analytics system integrates at these points:

1. **Supervisor.initialize()** - Create RunLogger
2. **Supervisor.process_issue()** - Create IssueTracker
3. **AgentExecutor.execute_*()** - Track agent start/end
4. **Pipeline monitoring** - Track pipeline attempts
5. **Error handling** - Start/end debugging cycles
6. **Supervisor cleanup** - Finalize run

## Future Enhancements

- Dashboard for visualizing metrics
- Automated performance analysis
- Alerts for anomalies
- Comparative analysis across runs
- Export to analytics platforms
