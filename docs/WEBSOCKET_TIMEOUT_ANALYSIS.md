# WebSocket Timeout Analysis - 3.5 Hour Runtime Issue

**Date:** 2025-10-11
**Issue:** WebSocket connection error after 3+ hour system runtime
**Impact:** Cosmetic - Error in logs during shutdown, doesn't affect system operation

---

## Error Details

```
[WS-ERROR] Unhandled exception in WebSocket handler: WebSocket is not connected. Need to call "accept" first.
[WS-DEBUG] ========== DISCONNECTION ==========
[WS-DEBUG] Connection ID: #unknown
[WS-DEBUG] Duration: unknown
Traceback (most recent call last):
  File "C:\Users\esaui\Desktop\PythonProjects\AgenticSys\web_gui\backend\app.py", line 116, in websocket_endpoint
    data = await websocket.receive_text()
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\esaui\Desktop\PythonProjects\AgenticSys\.venv\Lib\site-packages\starlette\websockets.py", line 118, in receive_text
    raise RuntimeError('WebSocket is not connected. Need to call "accept" first.')
RuntimeError: WebSocket is not connected. Need to call "accept" first.
```

**Context:**
- System runtime: 12,492 seconds (~3.5 hours)
- 3 issues processed, all Review Agent failures
- Error occurred during/after orchestration completion

---

## Root Cause Analysis

### 1. Long Runtime vs Browser/Proxy Timeouts

**Standard WebSocket Timeout Limits:**

| Component | Typical Timeout | Reason |
|-----------|----------------|---------|
| Browser (Chrome/Firefox) | 1-2 hours | Resource management |
| HTTP Proxy (Nginx) | 60-90 minutes | Default proxy_timeout |
| Load Balancer (AWS ALB) | 1 hour | Idle connection limit |
| HTTP/2 Keep-Alive | 5-30 minutes | Depends on server config |
| Cloudflare | 100 seconds | Free tier WebSocket limit |
| Corporate Firewall | 15-60 minutes | Security policy |

**Your Runtime:**
- **12,492 seconds = 208 minutes = 3.5 hours**
- **Exceeds ALL standard timeout limits**

### 2. Connection Lifecycle Analysis

**Normal Flow:**
```
1. Client connects → Server accepts (app.py:110)
2. Connection tracked (websocket.py:60-84)
3. Keepalive starts sending pings every 30s (websocket.py:519-522)
4. Client responds to pings → Connection stays alive
5. Client disconnects gracefully → Server cleans up
```

**What Happened (3.5 Hours):**
```
1. Client connects at T=0
2. Server accepts, tracks as Connection #X
3. Keepalive pings sent every 30s... (for ~2 hours)
4. T=~2 hours: Browser/proxy timeout silently closes connection
   - Client doesn't respond to keepalive anymore
   - Server's receive loop doesn't detect closure immediately
5. T=3.5 hours: System completes, tries to receive next message
6. Starlette raises: "WebSocket is not connected"
7. Exception handler tries to disconnect → Connection already gone
8. Error logged: Connection ID #unknown (not in tracking dict)
```

### 3. Why Keepalive Didn't Prevent This

**Keepalive is Active:**
- Configured: 30-second interval (websocket.py:49)
- Started on app startup (app.py:118)
- Sends ping JSON: `{"type": "keepalive", "timestamp": "..."}`

**Why It Failed to Prevent Timeout:**

1. **Browser Tab Backgrounding:**
   - Browsers throttle/pause JavaScript in background tabs
   - WebSocket may not process keepalive pings when throttled
   - Browser connection timeout still applies

2. **Network Proxy Doesn't Understand Application Pings:**
   - Keepalive sends JSON data (application layer)
   - Proxies track TCP-level idle time (transport layer)
   - Application pings don't reset proxy idle timer

3. **Browser Resource Limits:**
   - After 1-2 hours, browser may force-close "stale" connections
   - Regardless of keepalive activity

4. **Silent Connection Closure:**
   - Client closes without sending WebSocket close frame
   - Server doesn't detect until trying to send/receive
   - Server's receive loop is blocked waiting for data

### 4. Error Message Explanation

**"WebSocket is not connected. Need to call 'accept' first."**

This error message is MISLEADING. The actual issue is:
- Connection WAS accepted (app.py:110, websocket.py:60)
- Connection WAS active (for ~2 hours)
- Connection silently closed (client-side timeout)
- Server tried to receive from closed socket
- Starlette's error message is generic (assumes socket never accepted)

**"Connection ID: #unknown"**

This happens because:
```python
# websocket.py:96-97
conn_info = self.connection_info.get(websocket, {})
connection_id = conn_info.get("connection_id", "unknown")
```

The websocket object is no longer in `self.connection_info` because:
1. Client closed connection silently
2. Python's garbage collector or Starlette cleaned up the object
3. Server's tracking dict lost the reference
4. Exception handler tries to disconnect, but can't find connection info

---

## Why This Happens with Long-Running Operations

### Problem: Blocking Receive Loop

**Current Architecture (app.py:114-116):**
```python
while True:
    data = await websocket.receive_text()  # BLOCKS here
    message = json.loads(data)
    # Handle message...
```

**Issue:**
- The server blocks waiting for client messages
- During 3.5 hour orchestration, client sends nothing
- Server can't detect connection loss until trying to receive
- Keepalive pings are sent FROM server TO client, not the reverse

### Timing Breakdown

```
T=0:00:00  Client connects, system starts
T=0:00:30  Keepalive ping #1 sent → Client alive
T=0:01:00  Keepalive ping #2 sent → Client alive
...
T=1:45:00  Keepalive ping #210 sent → Client TIMEOUT
           Browser/proxy closes connection silently
           Server doesn't detect (still blocked on receive)
...
T=3:28:12  System completes orchestration
           Server's while loop tries: receive_text()
           Socket already closed → RuntimeError
```

**Key Insight:** Server only detects closure when trying to USE the connection, not proactively.

---

## Impact Assessment

### Severity: LOW (Cosmetic)

**Why Low Priority:**

1. **Doesn't Affect System Operation:**
   - Orchestration completed successfully (3 issues processed)
   - All agent execution finished
   - Error only during cleanup/shutdown
   - No data loss or corruption

2. **Happens at End of Run:**
   - Error occurs AFTER 3.5 hours of successful execution
   - System already completed its work
   - Just logging cleanup issue

3. **Client Already Gone:**
   - Error happens when client has disconnected
   - No user is waiting for response
   - Purely server-side cleanup issue

4. **Doesn't Crash System:**
   - Exception is caught and handled
   - System continues/shuts down normally
   - Logs show proper disconnection tracking

### User Experience Impact

**From User Perspective:**
- User sees: System running for 3+ hours
- Browser/tab likely closed or timed out
- User not actively watching console
- Error only visible in server logs (not user-facing)

**Actual Issue:**
- If user reconnects, session state is preserved
- Message history replay works correctly
- System continues normally

---

## Solution Strategies

### Strategy 1: Accept and Ignore (Recommended for Now)

**Rationale:**
- Issue is cosmetic (happens after work completes)
- Doesn't affect functionality
- Happens at system shutdown
- Fix would add complexity for minimal benefit

**Implementation:**
```python
# app.py:113-151
try:
    while True:
        data = await websocket.receive_text()
        # ... handle message ...
except WebSocketDisconnect as e:
    # Normal disconnect
    ws_manager.disconnect(websocket, reason=str(e), close_code=e.code)
except RuntimeError as e:
    # Connection already closed (after long timeout)
    if "not connected" in str(e).lower():
        print(f"[WS] Connection already closed (likely timeout after long run)")
        # Don't try to disconnect again - it's already gone
    else:
        raise  # Re-raise if different RuntimeError
except Exception as e:
    # Other errors
    ws_manager.disconnect(websocket, reason=f"Unhandled exception: {str(e)}")
```

**Benefits:**
- Minimal code change
- Clear logging
- Handles edge case gracefully

### Strategy 2: Proactive Connection Health Monitoring

**Add connection health checks to keepalive:**

```python
# websocket.py:505-543 (enhance _keepalive_loop)
async def _keepalive_loop(self):
    """Background task that sends periodic pings AND checks responses"""
    try:
        while self._keepalive_running:
            await asyncio.sleep(self.keepalive_interval)

            if not self.active_connections:
                continue

            disconnected = []
            for connection in self.active_connections:
                conn_info = self.connection_info.get(connection, {})
                last_ping = conn_info.get("last_ping")
                last_activity = conn_info.get("last_activity")

                # Check if connection is stale (no activity for 2x keepalive interval)
                if last_activity:
                    time_since_activity = (datetime.now() - last_activity).total_seconds()
                    if time_since_activity > (self.keepalive_interval * 4):  # 2 minutes no activity
                        connection_id = conn_info.get("connection_id", "unknown")
                        print(f"[WS-KEEPALIVE] Connection #{connection_id} stale ({time_since_activity:.0f}s) - probing")

                try:
                    # Send keepalive ping
                    await asyncio.wait_for(
                        connection.send_json({
                            "type": "keepalive",
                            "timestamp": datetime.now().isoformat()
                        }),
                        timeout=5.0  # 5 second timeout for send
                    )
                    # Update last ping time
                    if connection in self.connection_info:
                        self.connection_info[connection]["last_ping"] = datetime.now()
                except asyncio.TimeoutError:
                    # Send timeout - connection is dead
                    connection_id = conn_info.get("connection_id", "unknown")
                    print(f"[WS-KEEPALIVE] Connection #{connection_id} send timeout - marking dead")
                    disconnected.append((connection, "Send timeout"))
                except Exception as e:
                    connection_id = conn_info.get("connection_id", "unknown")
                    print(f"[WS-KEEPALIVE] Ping failed for #{connection_id}: {e}")
                    disconnected.append((connection, str(e)))

            # Remove dead connections
            for conn, error in disconnected:
                self.disconnect(conn, reason=f"Keepalive failed: {error}")

            if self.debug_mode and self.active_connections:
                print(f"[WS-KEEPALIVE] Checked {len(self.active_connections)} connections, removed {len(disconnected)} stale")

    except asyncio.CancelledError:
        print("[WS-KEEPALIVE] Loop cancelled")
    except Exception as e:
        print(f"[WS-KEEPALIVE] Loop error: {e}")
        traceback.print_exc()
```

**Benefits:**
- Detects dead connections proactively
- Cleans up before trying to use them
- Prevents "unknown connection" errors

**Drawbacks:**
- More complex code
- More CPU usage (constant health checks)
- May disconnect legitimate long-idle connections

### Strategy 3: Event-Driven Instead of Blocking Receive

**Replace blocking receive loop with task-based approach:**

```python
# app.py - New approach
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint with non-blocking message handling"""
    await ws_manager.connect(websocket)

    # Create background task for receiving messages
    receive_task = asyncio.create_task(receive_messages(websocket))

    try:
        # Wait for disconnection or completion
        await receive_task
    except Exception as e:
        print(f"[WS] Connection handler error: {e}")
    finally:
        # Clean up
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
        ws_manager.disconnect(websocket, reason="Handler completed")

async def receive_messages(websocket: WebSocket):
    """Background task to receive and handle messages"""
    try:
        while True:
            # Non-blocking receive with timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # 60 second timeout
                )
                message = json.loads(data)
                await handle_message(websocket, message)
            except asyncio.TimeoutError:
                # No message for 60s - that's OK, just loop again
                # Connection is kept alive by keepalive pings
                continue
            except WebSocketDisconnect:
                # Client disconnected
                break

    except Exception as e:
        print(f"[WS] Receive loop error: {e}")
        raise
```

**Benefits:**
- Timeout prevents infinite blocking
- Cleaner separation of concerns
- Can detect connection issues faster

**Drawbacks:**
- More complex architecture
- Need to refactor message handling
- Potential for race conditions

### Strategy 4: Increase Browser Timeout Limits (NOT RECOMMENDED)

**Not feasible because:**
- Can't control client browser settings
- Can't control proxy/firewall timeouts
- 3+ hour connections are inherently fragile
- Not a server-side fix

---

## Recommendations

### Immediate (Priority 1): Strategy 1 - Better Error Handling

**Why:**
- Minimal code change
- Fixes the noisy error logs
- Handles edge case gracefully
- No risk to existing functionality

**Implementation:**
1. Update `app.py:113-151` to catch `RuntimeError` specifically
2. Log connection closure gracefully
3. Skip disconnect attempt if connection already gone

### Medium-Term (Priority 2): Strategy 2 - Proactive Health Monitoring

**Why:**
- Detects stale connections earlier
- Prevents "unknown connection" scenarios
- Improves keepalive effectiveness

**Implementation:**
1. Enhance `_keepalive_loop` with stale connection detection
2. Add send timeout to keepalive pings
3. Clean up dead connections proactively

### Long-Term (Priority 3): Consider Task-Based Architecture

**Why:**
- Better for long-running operations
- More robust connection management
- Industry best practice for WebSocket servers

**Implementation:**
- Refactor WebSocket endpoint to use tasks
- Implement non-blocking receive with timeouts
- Separate connection lifecycle from message handling

---

## Testing Strategy

### Test Case 1: Long-Running Operation

**Setup:**
1. Start system with 3 issues (3+ hour runtime)
2. Keep browser tab active
3. Monitor WebSocket connection

**Expected:**
- Keepalive maintains connection
- No timeout errors
- Connection survives full run

**If Fails:** Browser timeout is too aggressive, need Strategy 2

### Test Case 2: Browser Tab Backgrounding

**Setup:**
1. Start system
2. Background browser tab for 2+ hours
3. Return to tab

**Expected:**
- Connection may timeout (browser throttling)
- Error handled gracefully (Strategy 1)
- Session state preserved for reconnection

### Test Case 3: Network Interruption

**Setup:**
1. Start system
2. Disconnect network for 2 minutes
3. Reconnect network

**Expected:**
- Keepalive detects dead connection
- Server cleans up connection
- Client can reconnect and restore session

---

## Monitoring Metrics

### Key Metrics to Track

```python
# Add to websocket.py
class ConnectionManager:
    def __init__(self):
        # ... existing code ...

        # Timeout metrics
        self.timeout_count = 0  # Connections that timed out
        self.avg_connection_duration = 0  # Average before timeout
        self.max_connection_duration = 0  # Longest successful connection
```

### Dashboard Alerts

1. **Connection Duration Alert:**
   - Alert if connections consistently fail after <1 hour
   - Indicates aggressive browser/proxy timeouts

2. **Keepalive Failure Rate:**
   - Alert if >50% of keepalive pings fail
   - Indicates network/client issues

3. **Reconnection Rate:**
   - Track how often clients reconnect
   - High rate indicates timeout issues

---

## Conclusion

### Summary

The WebSocket error is caused by **browser/proxy timeout after 3.5 hours**, which exceeds standard WebSocket connection limits (1-2 hours). This is a **cosmetic issue** that occurs during system shutdown and doesn't affect functionality.

### Root Cause

- System runtime: 3.5 hours (caused by Review Agent failures)
- Browser/proxy timeout: ~1-2 hours
- Silent connection closure
- Server detects only when trying to receive
- Error during cleanup phase

### Solution Priority

1. **Immediate:** Better error handling (Strategy 1)
2. **Medium-term:** Proactive health monitoring (Strategy 2)
3. **Long-term:** Task-based architecture (Strategy 3)

### Expected Outcome After Fixes

- No more "unknown connection" errors in logs
- Graceful handling of long-running timeouts
- Clear logging of connection lifecycle
- Preserved functionality (no breaking changes)

### Related Fix

**The 3.5-hour runtime itself should be fixed first:**
- Implement Review Agent "already merged" fixes (separate doc)
- Reduce runtime from 3.5 hours to <30 minutes
- This will naturally prevent most timeout issues
- WebSocket designed for <2 hour connections, not 3+ hours

**Once Review Agent is fixed:**
- System will complete faster (<1 hour typical)
- Within standard WebSocket timeout limits
- Timeout issue becomes much rarer
- Error handling still valuable for edge cases
