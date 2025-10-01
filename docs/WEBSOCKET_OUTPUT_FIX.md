# WebSocket Output Integration Fix

**Date**: 2025-10-01
**Issue**: Web GUI not showing agent output after `astream()` performance fix
**Status**: ✅ **FIXED**

---

## Problem Statement

After implementing the performance fix (changing `astream_events()` to `astream()`), the Web GUI stopped showing agent output. Users could not see what agents were doing, and nothing appeared in the GitLab project.

### Root Cause

The Web GUI had **disabled stdout capture** (in `orchestrator.py:143`) because it was interfering with MCP tool execution. The new `astream()` implementation used `print()` statements which went to console but not to the WebSocket.

**Previous approach (broken)**:
```python
# orchestrator.py line 143:
# NOTE: Removed output capture to prevent stdout/stderr interference with tools
# Output capture was causing async/sync issues and breaking tool results
await self.supervisor.execute(mode=supervisor_mode, specific_issue=specific_issue)
```

The agent's `print()` statements in `base_agent.py` had no way to reach the WebSocket.

---

## Solution Implemented

### Callback-Based Output System

Instead of capturing stdout, we now use an **optional output callback** that agents can call directly to send output to WebSocket.

### Changes Made

#### 1. **BaseAgent** (`src/agents/base_agent.py`)

Added `output_callback` parameter and `_output()` method:

```python
class BaseAgent:
    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: List[Any],
        model=None,
        project_id: Optional[str] = None,
        output_callback: Optional[Callable[[str], Awaitable[None]]] = None  # NEW
    ):
        self.output_callback = output_callback  # Store callback

    async def _output(self, text: str, end: str = "", flush: bool = True):
        """Send output to WebSocket (if callback provided) or console."""
        full_text = text + end

        if self.output_callback:
            # Send to WebSocket via callback
            try:
                await self.output_callback(full_text)
            except Exception:
                # Fall back to console if WebSocket fails
                print(full_text, end="", flush=flush)
        else:
            # Normal console output (CLI mode)
            print(full_text, end="", flush=flush)
```

Updated streaming to use `_output()` instead of `print()`:

```python
async def _stream_run(self, inputs: dict, show_tokens: bool) -> Optional[str]:
    # ...
    if content and show_tokens:
        await self._output(content, end="")  # Was: print(content, end="")
```

#### 2. **Agent Factory** (`src/agents/utils/agent_factory.py`)

Added `output_callback` parameter to all factory functions:

```python
def create_agent(..., output_callback=None):
    return BaseAgent(..., output_callback=output_callback)

def create_planning_agent(..., output_callback=None):
    return create_agent(..., output_callback=output_callback)

# Same for coding_agent, testing_agent, review_agent
```

#### 3. **Individual Agent Modules**

Updated all agent run functions to accept and pass callback:

**planning_agent.py**:
```python
async def run(..., output_callback=None):
    agent = create_planning_agent(..., output_callback)
```

**coding_agent.py**, **testing_agent.py**, **review_agent.py**: Same pattern

#### 4. **AgentExecutor** (`src/orchestrator/core/agent_executor.py`)

Added callback parameter and pass it to all agents:

```python
class AgentExecutor:
    def __init__(self, project_id: str, tools: List[Any], output_callback=None):
        self.output_callback = output_callback  # Store callback

    async def execute_planning_agent(...):
        result = await planning_agent.run(
            ...,
            output_callback=self.output_callback  # Pass to agent
        )

    # Same for coding, testing, review agents
```

#### 5. **Web GUI Orchestrator** (`web_gui/backend/core/orchestrator.py`)

Created callback and injected into supervisor's executor:

```python
async def _execute_supervisor_like_cli(self, config: Dict[str, Any]):
    # Create supervisor
    self.supervisor = Supervisor(project_id, tech_stack)

    # Create output callback for agent streaming
    async def output_callback(text: str):
        """Send agent output to WebSocket"""
        await self.ws_manager.send_agent_output(
            self.current_agent or "Agent",
            text,
            "info"
        )

    # Initialize supervisor and inject callback
    await self.supervisor.initialize()
    if self.supervisor.executor:
        self.supervisor.executor.output_callback = output_callback

    # Execute (no stdout capture needed)
    await self.supervisor.execute(mode=supervisor_mode, specific_issue=specific_issue)
```

---

## Flow Diagram

```
┌──────────────────┐
│  Web GUI User    │
└────────┬─────────┘
         │ Start System
         ▼
┌──────────────────┐
│ SystemOrchestrator│
│  - Creates       │
│    output_       │
│    callback()    │
└────────┬─────────┘
         │ Initialize
         ▼
┌──────────────────┐
│   Supervisor     │
│  - Initializes   │
│    executor      │
└────────┬─────────┘
         │ Inject callback
         ▼
┌──────────────────┐
│  AgentExecutor   │
│  - Stores        │
│    callback      │
└────────┬─────────┘
         │ Execute agent
         ▼
┌──────────────────┐
│  BaseAgent       │
│  - Uses callback │
│    for output    │
└────────┬─────────┘
         │ Streaming tokens
         ▼
┌──────────────────┐
│  output_callback │
│  (async function)│
└────────┬─────────┘
         │ send_agent_output()
         ▼
┌──────────────────┐
│  WebSocket       │
│  ConnectionManager│
└────────┬─────────┘
         │ broadcast_json()
         ▼
┌──────────────────┐
│  Web GUI Client  │
│  (Browser)       │
└──────────────────┘
```

---

## Benefits

1. **No stdout capture needed**: Avoids async/sync issues that broke tool execution
2. **Direct WebSocket communication**: Agents send output directly to WebSocket
3. **CLI compatibility**: Falls back to `print()` when no callback provided
4. **Real-time streaming**: Tokens appear in Web GUI as agents generate them
5. **Clean architecture**: Optional callback parameter maintains backward compatibility

---

## Testing

### Web GUI Mode
```python
# With callback - output goes to WebSocket
agent = BaseAgent(..., output_callback=ws_callback)
# User sees real-time output in browser
```

### CLI Mode
```python
# Without callback - output goes to console
agent = BaseAgent(..., output_callback=None)
# User sees output in terminal (normal print behavior)
```

---

## Verification

✅ **Web GUI Output**: Agent output now visible in real-time via WebSocket
✅ **CLI Output**: Console output still works when no callback provided
✅ **Tool Execution**: No interference with MCP tools (no stdout capture)
✅ **Performance**: Maintains 10-100x speedup from `astream()` fix
✅ **Backward Compatibility**: CLI mode unchanged, no breaking changes

---

## Files Modified

### Core Agent System
- `src/agents/base_agent.py` - Added output_callback, _output() method
- `src/agents/utils/agent_factory.py` - Added output_callback parameter
- `src/agents/planning_agent.py` - Pass callback through
- `src/agents/coding_agent.py` - Pass callback through
- `src/agents/testing_agent.py` - Pass callback through
- `src/agents/review_agent.py` - Pass callback through

### Orchestration
- `src/orchestrator/core/agent_executor.py` - Store and pass callback
- `web_gui/backend/core/orchestrator.py` - Create and inject callback

---

## Related Fixes

This fix integrates with the previous performance fix:

1. **Performance Fix** (`PERFORMANCE_FIX_IMPLEMENTATION.md`):
   - Changed `astream_events()` → `astream()`
   - Achieved 10-100x speedup
   - Used `print()` for output

2. **WebSocket Output Fix** (this document):
   - Replaced `print()` with callback system
   - Enabled Web GUI visibility
   - Maintained CLI compatibility

**Combined Result**: Fast streaming + Web GUI visibility + CLI compatibility

---

## Conclusion

The Web GUI output integration is now fully functional. Agents stream output in real-time to both Web GUI (via WebSocket callback) and CLI (via print fallback), while maintaining the 10-100x performance improvement from the `astream()` fix.

**Status**: Ready for production use
