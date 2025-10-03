# Logging & Metrics System Redesign

## Current Problems

### 1. Multiple Fragmented Logging Systems
- **223+ print statements** scattered across orchestrator code
- **RunLogger** - tracks run-level metadata (JSON files)
- **IssueTracker** - tracks issue-level metrics (JSON files)
- **CSVExporter** - exports metrics to CSV
- **WebSocket messages** - real-time GUI updates
- **MCP log callbacks** - MCP server logs

### 2. Critical Issues

#### A. No Centralized Control
```python
# Current state - can't control this easily
print("[INFO] Starting workflow...")
print(f"[CHECK] Issue #{issue_id}...")
await ws_manager.send_agent_output("Agent", "Working...", "info")
self.run_logger.add_issue(issue_id)
```
- Can't disable logs without editing code
- Can't filter by severity level
- Can't route to different destinations
- Can't correlate logs across components

#### B. Inconsistent Formatting
```python
# All different formats:
print("[INFO] Something")
print(f"[ISSUE #{id}] Working")
print("[WS-DEBUG] Connection")
print("Random unformatted message")
```
- No timestamps
- No severity levels
- No structured data
- Hard to parse

#### C. Mixing Concerns
```python
# Business logic + logging + metrics all mixed
print(f"[ISSUE #{issue_id}] Starting")  # Log
self.issue_tracker.start_agent("coding")  # Metric
await ws_manager.send_pipeline_update("coding", "running")  # GUI update
```

#### D. Missing Features
- ❌ No log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ❌ No correlation IDs (can't track a request across components)
- ❌ No structured logging (JSON format)
- ❌ No log rotation
- ❌ No context propagation
- ❌ No performance tracing
- ❌ Can't disable GUI logs in CLI mode
- ❌ Can't enable debug logs without code changes

---

## Proposed Architecture

### Design Principles

1. **Separation of Concerns**
   - **Logging** = What happened (for debugging, monitoring)
   - **Metrics** = How much/how many (for analytics, dashboards)
   - **Events** = State changes (for GUI updates, webhooks)

2. **Single Source of Truth**
   - One logger instance with multiple outputs
   - Structured data in, multiple formats out
   - Context flows through all systems

3. **Flexibility**
   - Easy to add new outputs (file, database, external services)
   - Easy to filter by level, component, context
   - Easy to switch between modes (CLI vs GUI)

---

## New Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Code                         │
│                                                              │
│  logger.info("Processing issue", issue_id=3, agent="coding")│
│  metrics.record_agent_start("coding", issue_id=3)           │
│  events.emit("agent_started", {...})                        │
└──────────────┬──────────────┬──────────────┬────────────────┘
               │              │              │
               ▼              ▼              ▼
     ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
     │   Logger    │  │   Metrics   │  │    Events    │
     │  (logging)  │  │(prometheus) │  │ (WebSocket)  │
     └──────┬──────┘  └──────┬──────┘  └──────┬───────┘
            │                │                 │
     ┌──────┴──────┐  ┌──────┴──────┐   ┌─────┴─────┐
     │             │  │             │   │           │
     ▼             ▼  ▼             ▼   ▼           ▼
 Console       File   CSV       Database  GUI    Webhooks
  (CLI)     (Rotating)(Excel)  (TimeSeries)
```

### 1. Unified Logger System

**File: `src/infrastructure/logging/logger.py`**

Features:
- Python's `logging` module with structured logging
- Multiple handlers (console, file, WebSocket, etc.)
- Context manager for automatic correlation IDs
- JSON formatting for structured data
- Severity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

```python
# Usage:
from src.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Starting workflow")

# Structured logging with context
logger.info("Processing issue", extra={
    "issue_id": 3,
    "agent": "coding",
    "project_id": "12345"
})

# With context manager (auto-adds correlation ID)
with logger.context(run_id="run_123", issue_id=3):
    logger.info("Starting coding")  # Auto-includes run_id and issue_id
    logger.debug("Reading file")    # Only shown if DEBUG enabled
```

### 2. Metrics System (Separate from Logging)

**File: `src/infrastructure/metrics/collector.py`**

Features:
- Counter metrics (issues processed, errors, successes)
- Gauge metrics (active agents, queue size)
- Histogram metrics (duration, retries)
- Export to CSV, Prometheus, TimeSeries DB

```python
# Usage:
from src.infrastructure.metrics import metrics

# Counters
metrics.increment("issues.processed", tags={"status": "success"})
metrics.increment("agent.executions", tags={"agent": "coding"})

# Gauges
metrics.set("active_agents", 3)

# Histograms
with metrics.timer("agent.duration", tags={"agent": "coding"}):
    # Do work
    pass

# Context manager
with metrics.context(run_id="run_123"):
    metrics.increment("issues.started")  # Auto-tagged with run_id
```

### 3. Event System (For GUI)

**File: `src/infrastructure/events/emitter.py`**

Features:
- Pub/sub pattern
- WebSocket handler subscribes to events
- Decouples business logic from GUI
- Can add more subscribers (webhooks, etc.)

```python
# Usage:
from src.infrastructure.events import events

# Emit events
events.emit("agent.started", {
    "agent": "coding",
    "issue_id": 3,
    "timestamp": "2025-10-03T14:30:00Z"
})

# Subscribe (in WebSocket manager)
events.subscribe("agent.*", ws_manager.handle_agent_event)
```

---

## Configuration System

**File: `config/logging.yaml`**

```yaml
logging:
  version: 1

  # Define severity levels per component
  loggers:
    root:
      level: INFO
      handlers: [console, file, websocket]

    src.orchestrator.supervisor:
      level: DEBUG  # More verbose for supervisor

    src.agents:
      level: INFO

    src.infrastructure.mcp_client:
      level: WARNING  # Less verbose for MCP

  # Define output handlers
  handlers:
    console:
      class: logging.StreamHandler
      level: INFO
      formatter: simple
      stream: ext://sys.stdout

    file:
      class: logging.handlers.RotatingFileHandler
      level: DEBUG
      formatter: json
      filename: logs/agenticsys.log
      maxBytes: 10485760  # 10MB
      backupCount: 5

    websocket:
      class: src.infrastructure.logging.handlers.WebSocketHandler
      level: INFO
      formatter: json

  # Define formatters
  formatters:
    simple:
      format: '[%(levelname)s] %(name)s: %(message)s'

    json:
      class: pythonjsonlogger.jsonlogger.JsonFormatter
      format: '%(asctime)s %(name)s %(levelname)s %(message)s'
```

**File: `config/metrics.yaml`**

```yaml
metrics:
  enabled: true

  exporters:
    - type: csv
      path: logs/metrics
      interval: 60  # Export every 60 seconds

    - type: console
      interval: 300  # Print to console every 5 minutes

    # Future: Prometheus, InfluxDB, etc.
    # - type: prometheus
    #   port: 9090

  collectors:
    - name: issues
      type: counter
      help: "Number of issues processed"
      labels: [status, project_id]

    - name: agent_duration
      type: histogram
      help: "Agent execution duration"
      labels: [agent, status]
      buckets: [1, 5, 10, 30, 60, 120, 300]
```

---

## Migration Plan

### Phase 1: Infrastructure Setup (Week 1)
1. ✅ Create logging infrastructure
   - `src/infrastructure/logging/logger.py`
   - `src/infrastructure/logging/handlers.py`
   - `src/infrastructure/logging/context.py`

2. ✅ Create metrics infrastructure
   - `src/infrastructure/metrics/collector.py`
   - `src/infrastructure/metrics/exporters.py`

3. ✅ Create event system
   - `src/infrastructure/events/emitter.py`
   - `src/infrastructure/events/subscribers.py`

### Phase 2: Integration (Week 2)
1. ✅ Replace print statements in critical paths
   - Supervisor: 95 statements → logger calls
   - Agent executor: 60 statements → logger calls
   - Issue manager: 14 statements → logger calls

2. ✅ Integrate with WebSocket
   - Subscribe WebSocket handler to events
   - Format events for GUI display

3. ✅ Migrate analytics
   - Keep RunLogger/IssueTracker for backward compatibility
   - Make them use new logger internally
   - Deprecate CSV exports in favor of metrics exporters

### Phase 3: Cleanup (Week 3)
1. ✅ Remove all print statements
2. ✅ Update documentation
3. ✅ Add examples and tests

---

## Benefits

### For Development
- ✅ Easy to debug with DEBUG logs
- ✅ Can filter logs by component
- ✅ Structured data in logs (searchable)
- ✅ Correlation IDs track requests across components

### For Production
- ✅ Can adjust log levels without redeploying
- ✅ Log rotation prevents disk fill
- ✅ Centralized logging makes troubleshooting easier
- ✅ Metrics separate from logs

### For GUI
- ✅ Clean event-driven architecture
- ✅ WebSocket gets only relevant events
- ✅ No mixing of console and GUI logs

### For Analytics
- ✅ CSV exports still work
- ✅ Metrics system more flexible
- ✅ Can add Prometheus, Grafana later
- ✅ Time-series data for trends

---

## Example: Before vs After

### Before (Current Mess)
```python
print(f"[ISSUE #{issue_id}] Starting coding phase")
self.issue_tracker.start_agent("coding")
await ws_manager.send_agent_output("Coding Agent", "Starting...", "info")

# Execute agent
result = await self.executor.execute_coding_agent(issue, branch)

print(f"[ISSUE #{issue_id}] Coding {'succeeded' if result else 'failed'}")
self.issue_tracker.end_agent("coding", result)
if result:
    self.run_logger.record_success()
else:
    self.run_logger.record_error()
await ws_manager.send_pipeline_update("coding", "completed" if result else "failed")
```

### After (Clean Architecture)
```python
logger.info("Starting coding phase", issue_id=issue_id)
metrics.increment("agent.started", tags={"agent": "coding", "issue": issue_id})
events.emit("agent.started", {"agent": "coding", "issue_id": issue_id})

# Execute agent (clean business logic)
with metrics.timer("agent.duration", tags={"agent": "coding"}):
    result = await self.executor.execute_coding_agent(issue, branch)

logger.info("Coding phase completed", issue_id=issue_id, success=result)
metrics.increment("agent.completed", tags={
    "agent": "coding",
    "status": "success" if result else "failed"
})
events.emit("agent.completed", {
    "agent": "coding",
    "issue_id": issue_id,
    "success": result
})
```

---

## Questions for User

1. **Do you want to keep CSV exports?**
   - Keep as-is for backward compatibility?
   - Migrate to proper metrics exporters?

2. **What log level for production?**
   - INFO (standard, less noise)
   - DEBUG (very verbose, for troubleshooting)

3. **Do you want external metrics backends later?**
   - Prometheus + Grafana dashboards?
   - InfluxDB time-series database?

4. **Should we keep RunLogger/IssueTracker or rewrite them?**
   - Keep and make them use new logger internally?
   - Deprecate and replace with metrics system?
