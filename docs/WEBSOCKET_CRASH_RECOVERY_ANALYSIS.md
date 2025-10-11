# WebSocket Crash Recovery & State Persistence Analysis

**Date:** 2025-10-11
**Question:** How to catch errors when WebSocket crashes/closes and ensure system continues work or restarts where it stopped?
**Answer:** System has **PARTIAL** recovery - WebSocket handles disconnects, but backend crashes lose all state. Resume capability not implemented.

---

## Executive Summary

### Current State

**WebSocket Layer:** ✅ **Handles disconnections** - Message history replay for reconnections
**Backend Layer:** ❌ **No crash recovery** - All orchestration state lost on backend crash
**Resume Capability:** ❌ **NOT IMPLEMENTED** - Code exists but shows warning: "Resume functionality is not currently implemented" (supervisor.py:380)

### Critical Findings

| Scenario | Current Behavior | Data Loss Risk |
|----------|------------------|----------------|
| **WebSocket disconnects** | ✅ Reconnect works → replay messages | None (messages replayed) |
| **Browser tab closes** | ✅ Reconnect works → replay messages | None (backend still running) |
| **Backend crashes (Python)** | ❌ All state lost | **HIGH** (everything in-memory) |
| **Server restart** | ❌ All state lost | **HIGH** (must restart from scratch) |
| **Network interruption (5min)** | ⚠️ Partial - depends on keepalive | Low-Moderate (reconnect may work) |

---

## Architecture Analysis

### 1. WebSocket Connection Management

**File:** `web_gui/backend/core/websocket.py`

#### Current Implementation

```python
class ConnectionManager:
    def __init__(self):
        # Connection tracking
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

        # 🔑 MESSAGE HISTORY FOR RECONNECTION
        self.message_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000  # Keep last 1000 messages

        # 🔑 SESSION STATE FOR RECONNECTION
        self.session_state = {
            "running": False,
            "current_stage": None,
            "current_agent": None,
            "current_issue": None,
            "current_branch": None,
            "config": None,
            "stats": {},
            "start_time": None,
            "completed_issues": [],  # Track completed across reconnections
            "failed_issues": []  # Track failed across reconnections
        }
```

**✅ GOOD - Reconnection Support:**

```python
async def connect(self, websocket: WebSocket):
    """Accept and store a new WebSocket connection"""
    await websocket.accept()
    self.active_connections.append(websocket)

    # 🔑 REPLAY MESSAGE HISTORY TO NEW CLIENT
    await self._replay_history(websocket)  # Line 84

async def _replay_history(self, websocket: WebSocket):
    """Replay stored message history to newly connected client"""
    print(f"[WS] Replaying {len(self.message_history)} messages to new client")

    for message in self.message_history:
        await websocket.send_text(json.dumps(message))
        await asyncio.sleep(0.001)  # Prevent overwhelming client
```

**✅ GOOD - Keepalive Mechanism:**

```python
async def _keepalive_loop(self):
    """Background task that sends periodic pings to keep connections alive"""
    while self._keepalive_running:
        await asyncio.sleep(self.keepalive_interval)  # 30 seconds

        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "keepalive",
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                # Connection dead - remove it
                self.disconnect(connection, reason=f"Keepalive ping failed: {error}")
```

**❌ LIMITATION - Memory Only:**
- Message history stored in RAM only
- Backend restart → all history lost
- No disk persistence

### 2. Backend Error Handling

**File:** `web_gui/backend/app.py`

#### WebSocket Endpoint Error Handling

```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await ws_manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle messages (start_system, stop_system, etc.)
            if message["type"] == "start_system":
                config = message.get("data", {}).get("config", {})
                await orchestrator.start(config)

    except WebSocketDisconnect as e:
        # ✅ HANDLES NORMAL DISCONNECTS
        print(f"[WS] Client disconnected: ({e.code}, '{e.reason}')")
        ws_manager.disconnect(websocket, reason=str(e), close_code=e.code)

    except Exception as e:
        # ⚠️ HANDLES ERRORS BUT DOESN'T PRESERVE STATE
        print(f"[WS-ERROR] Unhandled exception: {e}")
        traceback.print_exc()
        ws_manager.disconnect(websocket, reason=f"Unhandled exception: {str(e)}")
```

**❌ CRITICAL GAP:**
- Exception in WebSocket → disconnects client
- Orchestration continues in background (if already started)
- Client loses visibility into running system
- No way to reconnect to in-progress work

### 3. Orchestration State Management

**File:** `src/orchestrator/supervisor.py`

#### Current State Tracking

```python
class Supervisor:
    def __init__(self, project_id: str, ...):
        self.state = ExecutionState.INITIALIZING
        self.issue_manager = None  # Tracks completed/failed issues
        self.current_issue_tracker = None  # Per-issue metrics
        self.run_logger = RunLogger(project_id, config)  # Analytics
```

**✅ PARTIAL - Analytics Persistence:**

```python
# supervisor.py:318-322
if self.current_issue_tracker:
    issue_report = self.current_issue_tracker.finalize_issue('completed')
    self.csv_exporter.export_issue(self.run_logger.run_id, issue_report)
    self.run_logger.record_success()
```

**✅ PARTIAL - Incremental Saves:**

Metrics saved during execution:
- `logs/runs/{run_id}/issues/issue_{iid}_metrics.json` - Per-issue progress
- `logs/runs/{run_id}/issues/issue_{iid}_report.json` - Final reports
- `logs/csv/runs.csv` - Run summaries
- `logs/csv/issues.csv` - Issue summaries

**❌ CRITICAL GAP - No Resume Capability:**

```python
# supervisor.py:364-380
async def execute(self, mode: str = "implement", specific_issue: str = None, resume: bool = False):
    """Main execution flow using modular components"""
    print(f"Project: {self.project_id}")
    print(f"Mode: {mode}")
    print(f"State: {self.state.value}")

    if resume:
        # ❌ NOT IMPLEMENTED
        print("[WARNING] Resume functionality is not currently implemented")

    # Initialize (ALWAYS starts from scratch)
    await self.initialize()
```

**KEY PROBLEM:** Even though resume parameter exists, it's not implemented. System always starts from beginning.

### 4. Issue Tracking State Persistence

**File:** `src/orchestrator/analytics/issue_tracker.py`

#### What Gets Saved to Disk

```python
class IssueTracker:
    def _save_metrics(self):
        """Save current metrics to file (incremental updates)"""
        current_data = {
            'run_id': self.run_id,
            'issue_iid': self.issue_iid,
            'start_time': self.start_time.isoformat(),
            'agent_metrics': {
                'planning': {'attempts': 0, 'successes': 0, 'failures': 0, ...},
                'coding': {...},
                'testing': {...},
                'review': {...}
            },
            'pipeline_attempts': len(self.pipeline_attempts),
            'succeeded_pipelines': self.succeeded_pipelines,
            'failed_pipelines': self.failed_pipelines,
            'debugging_cycles': len(self.debugging_cycles),
            'errors': len(self.errors),
            'status': 'in_progress'  # ← Tracks if issue is incomplete
        }

        # ✅ SAVES TO DISK
        metrics_file = self.logs_dir / f"issue_{self.issue_iid}_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(current_data, f, indent=2)
```

**✅ GOOD - Incremental Persistence:**
- Metrics saved after each agent execution
- Pipeline attempts logged in real-time
- Errors tracked immediately

**✅ GOOD - Final Reports:**
```python
def finalize_issue(self, status: str):
    """Finalize issue tracking and write final report"""
    final_report = {
        'issue_iid': self.issue_iid,
        'status': status,  # 'completed', 'failed', or 'skipped'
        'duration_seconds': duration,
        'agent_metrics': {...},
        'pipeline_attempts': total_pipeline_attempts,
        'debugging_cycles': total_debugging_cycles,
        'errors': self.errors
    }

    # ✅ SAVES COMPREHENSIVE REPORT
    report_file = self.logs_dir / f"issue_{self.issue_iid}_report.json"
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2)
```

**❌ GAP - Not Used for Resume:**
- Files saved to disk contain ALL information needed to resume
- But supervisor doesn't read these files to resume work
- Data is only for analytics/post-mortem analysis

---

## Failure Scenarios Analysis

### Scenario 1: WebSocket Disconnects (Browser Tab Closed)

**What Happens:**
1. User closes browser tab
2. WebSocket connection lost → triggers `WebSocketDisconnect` exception
3. Connection manager removes connection: `ws_manager.disconnect(websocket)`
4. **Backend orchestration continues running** (not affected by WebSocket)
5. User reopens browser → new WebSocket connection
6. Connection manager replays message history (up to 1000 messages)
7. User sees current state restored

**Current Behavior:** ✅ **WORKS WELL**

**Data Loss:** **NONE** (backend still running, messages replayed)

**Code Path:**
```
User closes tab
  ↓
WebSocket disconnect (app.py:141)
  ↓
ws_manager.disconnect(websocket) (websocket.py:91)
  ↓
Backend continues: supervisor.execute() still running
  ↓
User opens new tab
  ↓
ws_manager.connect(new_websocket) (websocket.py:53)
  ↓
await _replay_history(new_websocket) (websocket.py:256)
  ↓
Client sees all previous messages + current state
```

### Scenario 2: Backend Python Process Crashes

**What Happens:**
1. Python process crashes (e.g., unhandled exception, OOM, killed by OS)
2. **ALL in-memory state lost:**
   - `supervisor.state` = lost
   - `issue_manager.completed_issues` = lost
   - `ws_manager.message_history` = lost
   - `ws_manager.session_state` = lost
   - Current agent execution = lost
3. Restart backend → everything reset
4. Client reconnects → receives empty history
5. **Must restart orchestration from scratch**

**Current Behavior:** ❌ **FAILS - Complete State Loss**

**Data Loss:** **HIGH** - Only completed issue reports saved, work-in-progress lost

**What's Saved to Disk:**
- ✅ Completed issue reports: `logs/runs/{run_id}/issues/issue_*.json`
- ✅ In-progress metrics: `logs/runs/{run_id}/issues/issue_{iid}_metrics.json`
- ❌ Current orchestration state: NOT SAVED
- ❌ Supervisor state: NOT SAVED
- ❌ Which issue was being processed: NOT SAVED
- ❌ Message history: NOT SAVED

**Code Evidence:**
```python
# supervisor.py:379-380
if resume:
    print("[WARNING] Resume functionality is not currently implemented")
    # ❌ Just prints warning, doesn't actually resume
```

### Scenario 3: Network Interruption (5 Minutes)

**What Happens:**
1. Network drops (Wi-Fi disconnect, VPN timeout, ISP outage)
2. WebSocket connection stalls
3. Keepalive pings fail after 30s
4. Connection manager detects failure: `disconnected.append((connection, error))`
5. Backend continues orchestration (not network-dependent for GitLab API calls if using MCP)
6. Network returns after 5 minutes
7. Client reconnects automatically (if client implements reconnect logic)
8. Message history replayed → user sees updated state

**Current Behavior:** ⚠️ **PARTIAL - Depends on Client**

**Data Loss:** **LOW** - Backend continues, just loses visibility

**Code Path:**
```
Network drops
  ↓
Keepalive ping fails (websocket.py:526)
  ↓
ws_manager.disconnect(conn, reason="Keepalive ping failed") (websocket.py:534)
  ↓
Backend continues: agents still executing
  ↓
Network returns
  ↓
Client reconnects (if implemented)
  ↓
History replayed (websocket.py:256)
  ↓
Client catches up with current state
```

**❌ DEPENDS ON:** Client must implement automatic reconnection logic

### Scenario 4: Server Restart (Deployment, Maintenance)

**What Happens:**
1. Admin restarts FastAPI server (e.g., code deployment)
2. All WebSocket connections closed
3. **ALL in-memory state lost** (same as Scenario 2)
4. Orchestration terminated mid-execution
5. On restart, empty state
6. Clients reconnect → see empty system
7. **Must restart orchestration manually**

**Current Behavior:** ❌ **FAILS - No Graceful Handoff**

**Data Loss:** **HIGH** - Same as backend crash

**Missing Feature:**
- No graceful shutdown (save state before exit)
- No checkpoint loading on startup

### Scenario 5: 3+ Hour Runtime with WebSocket Timeout

**What Happens:**
1. System runs for 3+ hours
2. Browser/proxy timeout closes WebSocket (as analyzed in WEBSOCKET_TIMEOUT_ANALYSIS.md)
3. Connection manager detects closure
4. Backend orchestration continues
5. User refreshes browser
6. Reconnects and sees current state (via message replay)

**Current Behavior:** ✅ **WORKS** (with cosmetic error in logs)

**Data Loss:** **NONE**

**Note:** This scenario was already analyzed in detail in `WEBSOCKET_TIMEOUT_ANALYSIS.md`.

---

## Root Causes of Recovery Gaps

### Root Cause 1: In-Memory Only Architecture

**Problem:** All orchestration state stored in RAM:

```python
# supervisor.py
class Supervisor:
    def __init__(self, ...):
        self.state = ExecutionState.INITIALIZING  # ← In-memory
        self.issue_manager = IssueManager(...)  # ← In-memory
        self.completed_issues = []  # ← In-memory
        self.run_logger = RunLogger(...)  # ← In-memory
```

**Impact:** Backend restart/crash = complete state loss

**Why Not Persisted:**
- Design choice: Optimize for runtime performance
- Assumption: Backend runs reliably without crashes
- Assumption: Full execution completes in one session

### Root Cause 2: No Checkpoint/Resume Logic

**Problem:** Resume parameter exists but not implemented:

```python
# supervisor.py:379-380
if resume:
    print("[WARNING] Resume functionality is not currently implemented")
    # ← Code to load checkpoint should be here, but isn't
```

**What's Missing:**
- Checkpoint creation: Save state at key milestones
- Checkpoint loading: Restore state on startup
- State reconciliation: Merge disk state with fresh start

### Root Cause 3: No Orchestration Recovery After WebSocket Error

**Problem:** WebSocket error doesn't trigger graceful handling:

```python
# app.py:147-151
except Exception as e:
    print(f"[WS-ERROR] Unhandled exception: {e}")
    traceback.print_exc()
    ws_manager.disconnect(websocket, reason=f"Unhandled exception: {str(e)}")
    # ← Should check if orchestration is running and handle gracefully
```

**Impact:** Client loses connection, but backend may still be working. No way to signal client to reconnect.

### Root Cause 4: Supervisor Not Monitoring WebSocket Health

**Problem:** Supervisor doesn't know if clients are connected:

```python
# supervisor.py - No check for client connectivity
async def implement_issue(self, issue: Dict, max_retries: int = None):
    for attempt in range(retries):
        # Execute agents...
        # ← No check: "Are any clients still connected?"
        # ← No handling: "If all clients disconnected, should we pause?"
```

**Impact:** Orchestration continues blindly even if all clients disconnected

---

## Solution Design: Crash Recovery & Resume

### Strategy 1: Checkpoint-Based Resume (RECOMMENDED)

**Goal:** Save orchestration state at key points, load on restart

#### Implementation Plan

**Phase 1: Checkpoint Creation**

```python
# New file: src/orchestrator/checkpoint.py

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class CheckpointManager:
    """Manages orchestration checkpoints for crash recovery"""

    def __init__(self, run_id: str, project_id: str):
        self.run_id = run_id
        self.project_id = project_id
        self.checkpoint_dir = Path(f'logs/runs/{run_id}/checkpoints')
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, state: Dict[str, Any]):
        """Save orchestration state to disk"""
        checkpoint = {
            'run_id': self.run_id,
            'project_id': self.project_id,
            'timestamp': datetime.now().isoformat(),
            'state': state
        }

        checkpoint_file = self.checkpoint_dir / 'latest.json'
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint, f, indent=2)

        print(f"[CHECKPOINT] Saved state to {checkpoint_file}")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load latest checkpoint if exists"""
        checkpoint_file = self.checkpoint_dir / 'latest.json'

        if not checkpoint_file.exists():
            return None

        with open(checkpoint_file, 'r') as f:
            checkpoint = json.load(f)

        print(f"[CHECKPOINT] Loaded state from {checkpoint_file}")
        return checkpoint

    def checkpoint_exists(self) -> bool:
        """Check if checkpoint exists"""
        return (self.checkpoint_dir / 'latest.json').exists()
```

**Phase 2: Integrate with Supervisor**

```python
# Modify supervisor.py

from .checkpoint import CheckpointManager

class Supervisor:
    def __init__(self, project_id: str, ...):
        # ... existing init ...
        self.checkpoint_manager = None  # Will be created after run_logger

    async def execute(self, mode: str = "implement", specific_issue: str = None, resume: bool = False):
        """Main execution flow with checkpoint support"""

        # Initialize checkpoint manager
        self.checkpoint_manager = CheckpointManager(self.run_logger.run_id, self.project_id)

        # CHECK FOR EXISTING CHECKPOINT
        if resume and self.checkpoint_manager.checkpoint_exists():
            print("[RESUME] Found existing checkpoint - loading state...")
            checkpoint = self.checkpoint_manager.load_checkpoint()
            await self._restore_from_checkpoint(checkpoint)
            print("[RESUME] State restored - continuing execution...")
        else:
            print("[NEW RUN] Starting fresh execution...")

        # ... rest of execution ...

    async def implement_issue(self, issue: Dict, max_retries: int = None) -> bool:
        """Implement a single issue with checkpointing"""
        issue_iid = get_issue_iid(issue)

        # CREATE CHECKPOINT BEFORE ISSUE
        self._save_checkpoint(f"before_issue_{issue_iid}")

        # ... existing implementation logic ...

        # CREATE CHECKPOINT AFTER ISSUE
        if success:
            self._save_checkpoint(f"after_issue_{issue_iid}_success")
        else:
            self._save_checkpoint(f"after_issue_{issue_iid}_failed")

        return success

    def _save_checkpoint(self, stage: str):
        """Save current state to checkpoint"""
        state = {
            'stage': stage,
            'execution_state': self.state.value,
            'completed_issues': [
                get_issue_iid(i) if isinstance(i, dict) else i
                for i in self.issue_manager.completed_issues
            ],
            'failed_issues': [
                get_issue_iid(i) if isinstance(i, dict) else i
                for i in self.issue_manager.failed_issues
            ],
            'current_plan': self.planning_manager.get_current_plan(),
            'run_metrics': {
                'start_time': self.run_logger.start_time.isoformat(),
                'total_successes': self.run_logger.total_successes,
                'total_errors': self.run_logger.total_errors
            }
        }

        self.checkpoint_manager.save_checkpoint(state)

    async def _restore_from_checkpoint(self, checkpoint: Dict[str, Any]):
        """Restore orchestration state from checkpoint"""
        state = checkpoint['state']

        # Restore execution state
        self.state = ExecutionState(state['execution_state'])

        # Restore completed/failed issues
        self.issue_manager.completed_issues = state['completed_issues']
        self.issue_manager.failed_issues = state['failed_issues']

        # Restore plan
        if state.get('current_plan'):
            self.planning_manager.store_plan(state['current_plan'])

        # Restore run metrics
        metrics = state['run_metrics']
        self.run_logger.total_successes = metrics['total_successes']
        self.run_logger.total_errors = metrics['total_errors']

        print(f"[RESUME] Restored state:")
        print(f"  - Completed issues: {len(self.issue_manager.completed_issues)}")
        print(f"  - Failed issues: {len(self.issue_manager.failed_issues)}")
        print(f"  - Last stage: {state['stage']}")
```

**Benefits:**
- Backend crashes → restart with `--resume` flag → continues where stopped
- Checkpoints saved after each issue → minimal work loss
- Works for both CLI and Web GUI

**Limitations:**
- Can't resume mid-agent execution (would lose LLM conversation context)
- Checkpoint granularity: per-issue, not per-agent-step

### Strategy 2: Persistent WebSocket State (COMPLEMENTARY)

**Goal:** Save WebSocket session state to disk for full recovery

```python
# Modify web_gui/backend/core/websocket.py

from pathlib import Path
import json

class ConnectionManager:
    def __init__(self):
        # ... existing init ...

        # Persistent state directory
        self.state_dir = Path('logs/websocket_sessions')
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Load previous session on startup
        self._load_session_state()

    def _save_session_state(self):
        """Save session state to disk"""
        state_file = self.state_dir / 'session_state.json'

        # Convert message history and session state to JSON
        data = {
            'message_history': self.message_history,
            'session_state': self.session_state,
            'saved_at': datetime.now().isoformat()
        }

        with open(state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_session_state(self):
        """Load session state from disk on startup"""
        state_file = self.state_dir / 'session_state.json'

        if not state_file.exists():
            print("[WS] No previous session state found")
            return

        with open(state_file, 'r') as f:
            data = json.load(f)

        self.message_history = data['message_history']
        self.session_state = data['session_state']

        print(f"[WS] Loaded session state from disk:")
        print(f"  - Message history: {len(self.message_history)} messages")
        print(f"  - System running: {self.session_state['running']}")
        print(f"  - Last saved: {data['saved_at']}")

    def _store_message(self, event_type: str, data: Any):
        """Store message in history and persist to disk"""
        # ... existing message storage code ...

        # ✅ NEW: Save to disk after storing
        self._save_session_state()
```

**Benefits:**
- Server restart → message history preserved
- Clients reconnect → see full history even after backend restart
- WebSocket state survives backend crashes

**Limitations:**
- Disk I/O overhead (mitigate with batching)
- Stale state if not cleared properly

### Strategy 3: Orchestration Health Monitoring (DEFENSIVE)

**Goal:** Detect and handle client disconnection gracefully

```python
# Modify supervisor.py

class Supervisor:
    def __init__(self, ...):
        # ... existing init ...
        self.ws_health_callback = None  # Will be set by orchestrator

    async def implement_issue(self, issue: Dict, max_retries: int = None) -> bool:
        """Implement a single issue with client health checks"""

        for attempt in range(retries):
            # CHECK CLIENT HEALTH BEFORE LONG OPERATION
            if self.ws_health_callback:
                clients_connected = await self.ws_health_callback()

                if clients_connected == 0:
                    print("[SUPERVISOR] No clients connected - pausing orchestration")
                    print("[SUPERVISOR] Waiting for client reconnection...")

                    # Wait for client (with timeout)
                    timeout = 300  # 5 minutes
                    for _ in range(timeout // 10):
                        await asyncio.sleep(10)
                        clients_connected = await self.ws_health_callback()
                        if clients_connected > 0:
                            print("[SUPERVISOR] Client reconnected - resuming")
                            break
                    else:
                        print("[SUPERVISOR] No client after 5min - saving checkpoint and exiting")
                        self._save_checkpoint("paused_no_clients")
                        return False

            # Continue with implementation...
```

**Benefits:**
- Detects when all clients disconnect
- Pauses orchestration instead of running blindly
- Saves checkpoint before exiting
- Allows graceful resume when client returns

### Strategy 4: Client-Side Reconnection Logic (COMPLEMENTARY)

**Goal:** Browser automatically reconnects when WebSocket closes

```javascript
// New file: web_gui/frontend/js/websocket_client.js

class ResilientWebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
        this.connected = false;
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('[WS] Connected');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            this.onConnected();
        };

        this.ws.onclose = (event) => {
            console.log(`[WS] Disconnected: ${event.code} - ${event.reason}`);
            this.connected = false;
            this.onDisconnected();

            // AUTOMATIC RECONNECTION
            this.reconnect();
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Error:', error);
            this.onError(error);
        };

        this.ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            this.onMessage(message);
        };
    }

    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('[WS] Max reconnection attempts reached');
            this.onMaxReconnectAttemptsReached();
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
            this.maxReconnectDelay
        );

        console.log(`[WS] Reconnecting in ${delay/1000}s (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            console.log('[WS] Attempting reconnection...');
            this.connect();
        }, delay);
    }

    send(data) {
        if (!this.connected || this.ws.readyState !== WebSocket.OPEN) {
            console.warn('[WS] Cannot send - not connected');
            return false;
        }

        this.ws.send(JSON.stringify(data));
        return true;
    }

    // Callbacks (override these)
    onConnected() {}
    onDisconnected() {}
    onMessage(message) {}
    onError(error) {}
    onMaxReconnectAttemptsReached() {}
}

// Usage:
const wsClient = new ResilientWebSocketClient('ws://localhost:8000/ws');
wsClient.onConnected = () => {
    console.log('Successfully connected!');
    // UI: Show "connected" indicator
};
wsClient.onDisconnected = () => {
    console.log('Connection lost - will retry automatically');
    // UI: Show "reconnecting..." indicator
};
wsClient.onMessage = (message) => {
    // Handle different message types
    if (message.type === 'session_restore') {
        console.log(`Restored session with ${message.data.history_count} messages`);
    }
};
wsClient.connect();
```

**Benefits:**
- Automatic reconnection with exponential backoff
- Handles transient network issues
- User doesn't need to manually refresh
- Resilient to temporary disconnections

---

## Recommended Implementation Plan

### Phase 1: Foundation (Week 1)
**Priority:** HIGH
**Goal:** Basic checkpoint/resume capability

1. ✅ Create `CheckpointManager` class
2. ✅ Integrate checkpoints into `Supervisor`
3. ✅ Save checkpoint after each issue completion
4. ✅ Implement `_restore_from_checkpoint()` method
5. ✅ Test resume with CLI: `python -m cli.main --resume`

**Expected Outcome:** Backend crashes → restart with --resume → continues from last issue

### Phase 2: WebSocket Resilience (Week 2)
**Priority:** HIGH
**Goal:** Graceful WebSocket reconnection

1. ✅ Persist WebSocket session state to disk
2. ✅ Load session state on backend startup
3. ✅ Implement client-side reconnection logic
4. ✅ Add "reconnecting..." UI indicator
5. ✅ Test: Close/reopen browser tab → session restored

**Expected Outcome:** Browser refresh → reconnects → sees current orchestration state

### Phase 3: Health Monitoring (Week 3)
**Priority:** MEDIUM
**Goal:** Detect client disconnection and pause gracefully

1. ✅ Add `ws_health_callback` to Supervisor
2. ✅ Check client connectivity before long operations
3. ✅ Pause orchestration if no clients (with timeout)
4. ✅ Save checkpoint before exiting
5. ✅ Add "orchestration paused - no clients" message

**Expected Outcome:** All clients disconnect → orchestration pauses → saves checkpoint → can resume later

### Phase 4: Advanced Recovery (Week 4)
**Priority:** LOW
**Goal:** Mid-agent checkpoint recovery

1. ⚠️ Save agent conversation state (LLM context)
2. ⚠️ Implement mid-agent resume (complex)
3. ⚠️ Handle partial file creation recovery
4. ⚠️ Reconcile GitLab state with checkpoint

**Expected Outcome:** Crash during agent execution → resume from that agent

**Note:** Phase 4 is complex due to LLM session statefulness. May not be worth the effort.

---

## Testing Strategy

### Test Case 1: Backend Crash During Orchestration

**Setup:**
1. Start orchestration with 5 issues
2. Let 2 issues complete successfully
3. Kill Python process (`kill -9 <pid>`)

**Without Fix (Current):**
- ❌ Restart backend → all state lost
- ❌ Must restart from issue #1
- ❌ 2 completed issues processed again

**With Fix (After Phase 1):**
- ✅ Restart backend with `--resume`
- ✅ Loads checkpoint → sees 2 issues completed
- ✅ Resumes from issue #3

### Test Case 2: WebSocket Disconnect During Long Run

**Setup:**
1. Start orchestration with long-running issue (30 min)
2. Close browser tab after 10 minutes
3. Reopen tab after 5 minutes

**Without Fix (Current):**
- ⚠️ Backend continues running (good)
- ❌ Client reconnects but sees empty state
- ❌ Must wait until orchestration completes to see results

**With Fix (After Phase 2):**
- ✅ Backend continues running
- ✅ Client reconnects automatically
- ✅ Message history replayed
- ✅ Sees current agent output in real-time

### Test Case 3: Server Restart (Deployment)

**Setup:**
1. Start orchestration
2. Admin deploys new code → restarts FastAPI server
3. Server comes back online

**Without Fix (Current):**
- ❌ All WebSocket state lost
- ❌ Orchestration terminated
- ❌ Must restart from beginning

**With Fix (After Phase 1 + 2):**
- ✅ Checkpoint saved before shutdown (graceful)
- ✅ WebSocket state loaded from disk
- ✅ Restart with `--resume` → continues

### Test Case 4: Network Interruption (5 Min)

**Setup:**
1. Start orchestration
2. Disconnect network for 5 minutes
3. Reconnect network

**Without Fix (Current):**
- ⚠️ Backend continues (if GitLab API cached)
- ❌ WebSocket closed, client doesn't reconnect
- ❌ User must manually refresh

**With Fix (After Phase 2):**
- ✅ Backend continues
- ✅ Client automatically reconnects
- ✅ History replayed
- ✅ User sees current state without refresh

---

## Monitoring & Alerts

### Key Metrics to Track

```python
# Add to websocket.py
class ConnectionManager:
    def get_resilience_metrics(self) -> Dict[str, Any]:
        """Get metrics for crash recovery monitoring"""
        return {
            'checkpoints': {
                'total_saved': self.checkpoint_count,
                'last_checkpoint': self.last_checkpoint_time.isoformat(),
                'checkpoint_size_bytes': self.last_checkpoint_size
            },
            'reconnections': {
                'total_reconnects': self.reconnection_count,
                'avg_reconnect_time_seconds': self.avg_reconnect_time,
                'failed_reconnects': self.failed_reconnect_count
            },
            'session_state': {
                'messages_in_history': len(self.message_history),
                'session_persisted': self.session_state_file.exists(),
                'last_persist_time': self.last_persist_time.isoformat()
            }
        }
```

### Dashboard Alerts

1. **Checkpoint Failures:**
   - Alert if checkpoint save fails
   - Indicates disk space or permission issues

2. **High Reconnection Rate:**
   - Alert if >5 reconnections in 10 minutes
   - Indicates network instability

3. **Long Resume Time:**
   - Alert if checkpoint load takes >30 seconds
   - Indicates large state or disk performance issues

4. **No Checkpoint in 30 Min:**
   - Alert if running but no checkpoint saved
   - Indicates checkpoint mechanism broken

---

## Conclusion

### Current State Assessment

| Feature | Status | Risk Level |
|---------|--------|------------|
| **WebSocket Reconnection** | ✅ Implemented | Low |
| **Message History Replay** | ✅ Implemented | Low |
| **Backend Crash Recovery** | ❌ Not Implemented | **HIGH** |
| **Checkpoint/Resume** | ❌ Not Implemented | **HIGH** |
| **Client Auto-Reconnect** | ❌ Not Implemented | Medium |
| **Health Monitoring** | ❌ Not Implemented | Medium |

### Critical Gaps

1. **Backend crash = complete state loss** (HIGH RISK)
2. **No resume capability despite parameter existing** (HIGH RISK)
3. **Client must manually reconnect** (MEDIUM RISK)
4. **Orchestration runs blindly if all clients disconnect** (MEDIUM RISK)

### Recommended Actions

**IMMEDIATE (Priority 1):**
- Implement checkpoint/resume (Phase 1)
- Test with intentional backend crashes

**HIGH PRIORITY (Priority 2):**
- Persist WebSocket session state
- Implement client auto-reconnect
- Test with browser refresh scenarios

**MEDIUM PRIORITY (Priority 3):**
- Add client health monitoring
- Pause orchestration if no clients
- Test with 5-minute network interruption

**LOW PRIORITY (Priority 4):**
- Mid-agent checkpoint recovery
- Consider only if crashes during agent execution are common

### Expected Outcomes After Implementation

✅ Backend crashes → restart with --resume → continues where stopped
✅ Browser refresh → auto-reconnect → sees current state
✅ Network interruption → auto-reconnect → no manual refresh needed
✅ All clients disconnect → orchestration pauses → saves checkpoint
✅ Server restart → loads checkpoint + session → minimal disruption

**Implementation Time:** 3-4 weeks for Phases 1-3, 1-2 weeks for Phase 4 (if needed)
