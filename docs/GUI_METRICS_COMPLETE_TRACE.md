# GUI Metrics & Logging - Complete Trace & Analysis

## Investigation Date: 2025-10-11

## Purpose
Comprehensive investigation of ALL metrics and logs displayed in the GUI, tracing each from source to display, identifying issues and fixes needed.

---

## Metrics & Displays in GUI

### 1. Status Bar Displays

| Display | Element ID | Description |
|---------|-----------|-------------|
| System Status | `systemStatus` | Running/Idle status |
| Current Agent | `currentAgent` | Active agent name |
| Current Stage | `currentStage` | Pipeline stage (planning/coding/testing/review) |
| Progress | `progressBar`, `progressText` | Overall progress percentage |
| Current Issue | `currentIssue` | Issue number being processed |
| Current Branch | `currentBranch` | Git branch name |

### 2. Pipeline Stages

| Stage | Element ID | Statuses |
|-------|-----------|----------|
| Planning | `stage-planning` | pending/running/completed/failed |
| Coding | `stage-coding` | pending/running/completed/failed |
| Testing | `stage-testing` | pending/running/completed/failed |
| Review | `stage-review` | pending/running/completed/failed |

### 3. Statistics

| Stat | Element ID | Description |
|------|-----------|-------------|
| Total Issues | `statTotalIssues` | Total issues to process |
| Processed | `statProcessed` | Number of processed issues |
| Success Rate | `statSuccessRate` | Percentage of successful issues |
| Agent Calls | `statAgentCalls` | Number of agent invocations |
| Tool Calls | `statToolCalls` | Number of tool uses |
| Uptime | `statUptime` | System uptime (HH:MM:SS) |

### 4. Output & Logs

| Output | Element ID | Description |
|--------|-----------|-------------|
| Agent Output | `agentOutput` | Agent messages and responses |
| MCP Logs | `mcpLogsOutput` | MCP server logs |

---

## Complete Data Flow Traces

### ✅ TRACE 1: System Status (systemStatus)

**Display**: `<span id="systemStatus">Idle</span>`

**Data Flow**:
1. **Source**: `orchestrator.py:68-72, 86-89`
   ```python
   await self.ws_manager.send_system_status({
       "running": True,
       "message": "System starting...",
       "config": config
   })
   ```

2. **WebSocket**: `websocket.py:348-350`
   ```python
   async def send_system_status(self, status: Dict[str, Any]):
       await self.send_event("system_status", status)
   ```

3. **Frontend Handler**: `app.js:65-97`
   ```javascript
   this.ws.on('system_status', (data) => {
       this.handleSystemStatus(data);
   });

   handleSystemStatus(status) {
       this.ui.updateSystemStatus(status.running ? 'running' : 'idle');
   }
   ```

4. **UI Update**: `ui.js:122-132`
   ```javascript
   updateSystemStatus(status) {
       this.elements.systemStatus.textContent = status.charAt(0).toUpperCase() + status.slice(1);

       if (status === 'running') {
           this.elements.startBtn.disabled = true;
           this.elements.stopBtn.disabled = false;
       } else {
           this.elements.startBtn.disabled = false;
           this.elements.stopBtn.disabled = true;
       }
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

---

### ✅ TRACE 2: Current Agent (currentAgent)

**Display**: `<span id="currentAgent">-</span>`

**Data Flow**:
1. **Source**: `orchestrator.py:364-365` (NOT CALLED DIRECTLY)
   ```python
   self.current_agent = f"{stage}_agent"
   ```

2. **Issue**: Agent name is set in orchestrator but NOT sent via WebSocket!

3. **Workaround**: Frontend receives it via `agent_output` events:
   ```javascript
   this.ws.on('agent_output', (data) => {
       this.ui.updateCurrentAgent(data.agent);
   });
   ```

**Status**: ⚠️ **WORKS BUT INDIRECT** - Agent name comes from output events, not dedicated status updates

---

### ❌ TRACE 3: Current Stage (currentStage)

**Display**: `<span id="currentStage">-</span>`

**Data Flow**:
1. **Source**: `orchestrator.py:363`
   ```python
   self.current_stage = stage
   ```

2. **Issue**: Current stage is stored but NEVER sent to WebSocket!

3. **Workaround**: Pipeline update events indicate stage status:
   ```python
   await self.ws_manager.send_pipeline_update(stage, "running")
   ```

4. **Frontend receives**: `pipeline_update` events and updates stage status, but does NOT update `currentStage` element!

**Status**: ❌ **NOT WORKING** - `currentStage` element is NEVER updated!

---

### ✅ TRACE 4: Progress (progressBar, progressText)

**Display**: `<div id="progressBar"></div>` and `<span id="progressText">0%</span>`

**Data Flow**:
1. **Source**: `orchestrator.py:292-295`
   ```python
   progress = (i / len(issues)) * 100
   await self.ws_manager.send_system_status({
       "running": True,
       "progress": progress,
       "stats": self.stats
   })
   ```

2. **Frontend Handler**: `app.js:81-83`
   ```javascript
   if (status.progress !== undefined) {
       this.ui.updateProgress(status.progress);
   }
   ```

3. **UI Update**: `ui.js:134-137`
   ```javascript
   updateProgress(progress) {
       this.elements.progressBar.style.width = `${progress}%`;
       this.elements.progressText.textContent = `${Math.round(progress)}%`;
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

---

### ✅ TRACE 5: Current Issue (currentIssue)

**Display**: `<span id="currentIssue">-</span>`

**Data Flow**:
1. **Source**: `orchestrator.py:318-325`
   ```python
   await self.ws_manager.send_system_status({
       "running": True,
       "current_issue": issue_id,
       "current_branch": self.current_branch,
       "message": f"Processing issue #{issue_id} in branch {self.current_branch}"
   })
   ```

2. **Frontend Handler**: `app.js:73-75`
   ```javascript
   if (status.current_issue !== undefined) {
       this.ui.updateCurrentIssue(status.current_issue);
   }
   ```

3. **UI Update**: `ui.js:147-152`
   ```javascript
   updateCurrentIssue(issue) {
       const currentIssueEl = document.getElementById('currentIssue');
       if (currentIssueEl) {
           currentIssueEl.textContent = issue ? `#${issue}` : '-';
       }
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

---

### ✅ TRACE 6: Current Branch (currentBranch)

**Display**: `<span id="currentBranch">-</span>`

**Data Flow**:
1. **Source**: `orchestrator.py:318-325` (same as Current Issue)
   ```python
   await self.ws_manager.send_system_status({
       "running": True,
       "current_issue": issue_id,
       "current_branch": self.current_branch,
   })
   ```

2. **Frontend Handler**: `app.js:77-79`
   ```javascript
   if (status.current_branch !== undefined) {
       this.ui.updateCurrentBranch(status.current_branch);
   }
   ```

3. **UI Update**: `ui.js:154-159`
   ```javascript
   updateCurrentBranch(branch) {
       const currentBranchEl = document.getElementById('currentBranch');
       if (currentBranchEl) {
           currentBranchEl.textContent = branch || '-';
       }
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

---

### ✅ TRACE 7: Pipeline Stages (stage-planning, etc.)

**Display**: `<div id="stage-planning" data-status="pending">`

**Data Flow**:
1. **Source**: `orchestrator.py:365-367`
   ```python
   await self.ws_manager.send_pipeline_update(stage, "running")
   ```

2. **WebSocket**: `websocket.py:340-346`
   ```python
   async def send_pipeline_update(self, stage: str, status: str, details: Dict[str, Any] = None):
       await self.send_event("pipeline_update", {
           "stage": stage,
           "status": status,
           "details": details or {}
       })
   ```

3. **Frontend Handler**: `app.js:131-136`
   ```javascript
   this.ws.on('pipeline_update', (data) => {
       this.ui.updatePipelineStage(data.stage, data.status);
       if (data.status === 'running') {
           this.ui.updateCurrentStage(data.stage);
       }
   });
   ```

4. **UI Update**: `ui.js:179-189`
   ```javascript
   updatePipelineStage(stageName, status) {
       const stage = this.elements.stages[stageName];
       if (!stage) return;

       stage.setAttribute('data-status', status);
       const statusElement = stage.querySelector('.stage-status');
       if (statusElement) {
           statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
       }
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

**Note**: ✅ **FIX FOUND!** `updateCurrentStage()` IS called in pipeline_update handler!

---

### ⚠️ TRACE 8: Statistics - Total Issues (statTotalIssues)

**Display**: `<div id="statTotalIssues">0</div>`

**Data Flow**:
1. **Source**: `orchestrator.py:282, 310`
   ```python
   self.stats["total_issues"] = len(issues)  # For implement_all
   self.stats["total_issues"] = 1            # For single_issue
   ```

2. **Sent**: `orchestrator.py:292-298`
   ```python
   await self.ws_manager.send_system_status({
       "running": True,
       "progress": progress,
       "stats": self.stats
   })
   ```

3. **Frontend Handler**: `app.js:85-87`
   ```javascript
   if (status.stats) {
       this.ui.updateStatistics(status.stats);
   }
   ```

4. **UI Update**: `ui.js:267-280`
   ```javascript
   updateStatistics(stats) {
       if (stats.total_issues !== undefined) {
           this.elements.stats.totalIssues.textContent = stats.total_issues;
       }
   }
   ```

**Status**: ⚠️ **PARTIALLY WORKING** - Only updated for `implement_all` mode, NOT for `single_issue` mode during execution!

**Issue**: Total issues is set to 1 but never sent via WebSocket in single_issue mode.

---

### ❌ TRACE 9: Statistics - Agent Calls (statAgentCalls)

**Display**: `<div id="statAgentCalls">0</div>`

**Data Flow**:
1. **Source**: `orchestrator.py:407`
   ```python
   self.stats["agent_calls"] += 1
   ```

2. **Issue**: Agent calls are incremented but stats are ONLY sent during `_process_all_issues()`, NOT during `_execute_supervisor_like_cli()`!

3. **Result**: For `single_issue` mode (which uses `_execute_supervisor_like_cli`), agent calls are NEVER sent to frontend!

**Status**: ❌ **NOT WORKING** - Agent calls NOT tracked/displayed for single_issue mode!

---

### ❌ TRACE 10: Statistics - Tool Calls (statToolCalls)

**Display**: `<div id="statToolCalls">0</div>`

**Data Flow**:
1. **Source**: `orchestrator.py:51`
   ```python
   "tool_calls": 0
   ```

2. **Issue**: Tool calls are NEVER incremented anywhere in the code!

3. **Expected location**: Should be tracked in tool execution, but no code exists for this.

**Status**: ❌ **NOT IMPLEMENTED** - Tool calls counter does NOTHING!

---

### ✅ TRACE 11: Statistics - Uptime (statUptime)

**Display**: `<div id="statUptime">00:00:00</div>`

**Data Flow**:
1. **Source**: FRONTEND ONLY - No backend tracking!

2. **Frontend**: `app.js:100-109`
   ```javascript
   startUptimeCounter() {
       this.stopUptimeCounter();

       this.uptimeInterval = setInterval(() => {
           if (this.startTime) {
               const uptime = Math.floor((Date.now() - this.startTime) / 1000);
               this.ui.updateUptime(uptime);
           }
       }, 1000);
   }
   ```

3. **UI Update**: `ui.js:288-298`
   ```javascript
   updateUptime(seconds) {
       const hours = Math.floor(seconds / 3600);
       const minutes = Math.floor((seconds % 3600) / 60);
       const secs = seconds % 60;

       const formatted = [hours, minutes, secs]
           .map(v => v.toString().padStart(2, '0'))
           .join(':');

       this.elements.stats.uptime.textContent = formatted;
   }
   ```

**Status**: ✅ **WORKING CORRECTLY** - Tracked entirely in frontend

---

### ✅ TRACE 12: Agent Output (agentOutput)

**Display**: `<div id="agentOutput"></div>`

**Data Flow**:
1. **Source**: Multiple locations (agents send via callback)
   - `base_agent.py:_output()` → `output_callback`
   - Orchestrator callbacks

2. **WebSocket**: `websocket.py:322-328`
   ```python
   async def send_agent_output(self, agent: str, content: str, level: str = "info"):
       await self.send_event("agent_output", {
           "agent": agent,
           "content": content,
           "level": level
       })
   ```

3. **Frontend Handler**: `app.js:62-105`
   ```javascript
   this.ws.on('agent_output', (data) => {
       this.ui.addAgentOutput(data.agent, data.content, data.level);
   });
   ```

4. **UI Update**: `ui.js:202-222`
   ```javascript
   addAgentOutput(agent, content, level = 'info', timestamp = null) {
       const time = timestamp || new Date().toLocaleTimeString();
       const entry = document.createElement('div');
       entry.className = 'output-entry';
       entry.innerHTML = `
           <div class="output-header">
               <span class="output-agent">[${agent}]</span>
               <span class="output-timestamp">${time}</span>
           </div>
           <div class="output-content ${level}">${this.escapeHtml(content)}</div>
       `;

       this.elements.agentOutput.appendChild(entry);
       this.elements.agentOutput.scrollTop = this.elements.agentOutput.scrollHeight;
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

---

### ✅ TRACE 13: MCP Logs (mcpLogsOutput)

**Display**: `<div id="mcpLogsOutput"></div>`

**Data Flow**:
1. **Source**: MCP client via callback
   - `orchestrator.py:190-192`
   ```python
   async def mcp_log_callback(message: str, level: str = "info"):
       await self.ws_manager.send_mcp_log(message, level)
   ```

2. **WebSocket**: `websocket.py:392-397`
   ```python
   async def send_mcp_log(self, message: str, level: str = "info"):
       await self.send_event("mcp_log", {
           "message": message,
           "level": level
       })
   ```

3. **Frontend Handler**: `app.js:122-128`
   ```javascript
   this.ws.on('mcp_log', (data) => {
       this.ui.addMCPLog(
           data.message,
           data.level || 'info',
           data.timestamp
       );
   });
   ```

4. **UI Update**: `ui.js:224-251`
   ```javascript
   addMCPLog(message, level = 'info', timestamp = null) {
       const time = timestamp || new Date().toLocaleTimeString();
       const entry = document.createElement('div');
       entry.className = `output-entry level-${level}`;

       let icon = '[i]';
       if (level === 'error') icon = '[X]';
       else if (level === 'warning') icon = '[!]';
       else if (level === 'success') icon = '[✓]';
       else if (level === 'debug') icon = '[D]';

       entry.innerHTML = `
           <span class="output-time">${time}</span>
           <span class="output-agent">[MCP]</span>
           <span class="output-icon">${icon}</span>
           <span class="output-text">${this.escapeHtml(message)}</span>
       `;

       this.elements.mcpLogsOutput.appendChild(entry);
       this.elements.mcpLogsOutput.scrollTop = this.elements.mcpLogsOutput.scrollHeight;
   }
   ```

**Status**: ✅ **WORKING CORRECTLY**

---

## Summary of Issues Found

| # | Metric/Display | Status | Issue | Priority |
|---|---------------|--------|-------|----------|
| 1 | System Status | ✅ Working | None | - |
| 2 | Current Agent | ⚠️ Indirect | Comes from agent_output, not dedicated status | Low |
| 3 | Current Stage | ✅ Working | Actually works via pipeline_update! | - |
| 4 | Progress | ✅ Working | None | - |
| 5 | Current Issue | ✅ Working | None | - |
| 6 | Current Branch | ✅ Working | None | - |
| 7 | Pipeline Stages | ✅ Working | None | - |
| 8 | Total Issues | ⚠️ Partial | Not sent for single_issue mode | Medium |
| 9 | Processed Issues | ⚠️ Partial | Not sent for single_issue mode | Medium |
| 10 | Success Rate | ⚠️ Partial | Not sent for single_issue mode | Medium |
| 11 | Agent Calls | ❌ Broken | Not tracked for single_issue mode | **HIGH** |
| 12 | Tool Calls | ❌ Not Implemented | Never incremented anywhere | **HIGH** |
| 13 | Uptime | ✅ Working | Frontend-only tracking | - |
| 14 | Agent Output | ✅ Working | None | - |
| 15 | MCP Logs | ✅ Working | None | - |

---

## Critical Issues

### ❌ Issue 1: Statistics Not Sent in Single Issue Mode

**Problem**: When using `single_issue` mode, statistics are never sent via WebSocket during execution because `_execute_supervisor_like_cli()` doesn't send periodic status updates.

**Location**: `orchestrator.py:111-192`

**Fix Needed**:
```python
async def _execute_supervisor_like_cli(self, config: Dict[str, Any]):
    # ... existing code ...

    # Initialize stats for single issue
    self.stats["total_issues"] = 1

    # Send initial stats
    await self.ws_manager.send_system_status({
        "running": True,
        "stats": self.stats
    })

    # ... execute supervisor ...

    # Send final stats
    await self.ws_manager.send_system_status({
        "running": False,
        "stats": self.stats
    })
```

---

### ❌ Issue 2: Agent Calls Not Tracked

**Problem**: `agent_calls` is incremented in `_run_stage()` (line 407), but `_run_stage()` is ONLY used by `_process_issue()`, which is ONLY called in `implement_all` mode. Single issue mode never increments this.

**Location**: `orchestrator.py:407`

**Fix Needed**: Track agent calls in supervisor execution callback or after each agent run.

---

### ❌ Issue 3: Tool Calls Never Tracked

**Problem**: `tool_calls` counter exists but is NEVER incremented anywhere in the codebase!

**Location**: Nowhere - not implemented

**Fix Needed**: Track tool calls via tool monitor or execution callback.

**Possible Implementation**:
```python
# In orchestrator or tool monitor
async def track_tool_call(self, agent: str, tool: str):
    self.stats["tool_calls"] += 1
    # Send update
    await self.ws_manager.send_system_status({
        "running": True,
        "stats": self.stats
    })
```

---

## Recommendations

### Priority 1: Fix Statistics for Single Issue Mode

Add periodic status updates during supervisor execution in `_execute_supervisor_like_cli()`.

### Priority 2: Implement Tool Calls Tracking

Add tool call tracking in the agent execution layer or supervisor.

### Priority 3: Track Agent Calls Consistently

Ensure agent calls are tracked regardless of execution mode.

---

## Testing Checklist

- [ ] Verify System Status updates correctly
- [ ] Verify Current Agent shows agent name
- [ ] Verify Current Stage updates during pipeline
- [ ] Verify Progress bar updates
- [ ] Verify Current Issue displays issue number
- [ ] Verify Current Branch displays branch name
- [ ] Verify Pipeline stages update (pending/running/completed/failed)
- [ ] Verify Total Issues shows correct count (both modes)
- [ ] Verify Processed Issues increments
- [ ] Verify Success Rate calculates correctly
- [ ] **Verify Agent Calls increments (NEEDS FIX)**
- [ ] **Verify Tool Calls increments (NEEDS IMPLEMENTATION)**
- [ ] Verify Uptime counts correctly
- [ ] Verify Agent Output displays messages
- [ ] Verify MCP Logs display

---

**Investigation Complete**: 2025-10-11
**Critical Issues Found**: 3
**Working Correctly**: 12/15
**Needs Fixing**: 3/15

