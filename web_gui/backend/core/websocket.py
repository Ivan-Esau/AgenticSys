"""
WebSocket connection manager for real-time updates
Enhanced with comprehensive debugging for connection lifecycle tracking
"""

from typing import List, Dict, Any, Optional
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
import traceback
from fastapi.encoders import jsonable_encoder


class ConnectionManager:
    """Manages WebSocket connections for real-time communication"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

        # Session persistence: Store message history for reconnection
        self.message_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000  # Keep last 1000 messages

        # Session state for reconnection
        self.session_state = {
            "running": False,
            "current_stage": None,
            "current_agent": None,
            "current_issue": None,
            "current_branch": None,
            "config": None,
            "stats": {},
            "start_time": None,
            "completed_issues": [],  # Track completed issues across reconnections
            "failed_issues": []  # Track failed issues across reconnections
        }

        # Debugging: Connection lifecycle tracking
        self.connection_counter = 0  # Total connections since server start
        self.disconnection_log: List[Dict[str, Any]] = []
        self.max_disconnect_log = 50  # Keep last 50 disconnections

        # Debugging: Enable verbose logging
        self.debug_mode = True  # Set to False to reduce console output

        # Keepalive configuration
        self.keepalive_interval = 30  # Send ping every 30 seconds
        self.keepalive_task = None
        self._keepalive_running = False

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection"""
        connection_time = datetime.now()
        self.connection_counter += 1
        connection_id = self.connection_counter

        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            self.connection_info[websocket] = {
                "connection_id": connection_id,
                "connected_at": connection_time,
                "last_ping": connection_time,
                "last_activity": connection_time,
                "messages_sent": 0,
                "messages_received": 0,
                "client_state": websocket.client.host if websocket.client else "unknown"
            }

            if self.debug_mode:
                print(f"[WS-DEBUG] ========== NEW CONNECTION ==========")
                print(f"[WS-DEBUG] Connection ID: #{connection_id}")
                print(f"[WS-DEBUG] Client: {websocket.client.host if websocket.client else 'unknown'}:{websocket.client.port if websocket.client else 'unknown'}")
                print(f"[WS-DEBUG] Time: {connection_time.isoformat()}")
                print(f"[WS-DEBUG] Total Active: {len(self.active_connections)}")
                print(f"[WS-DEBUG] Total Since Start: {self.connection_counter}")
                print(f"[WS-DEBUG] ======================================")
            else:
                print(f"[WS] Client connected. Total connections: {len(self.active_connections)}")

            # Replay message history for reconnection
            await self._replay_history(websocket)

        except Exception as e:
            print(f"[WS-ERROR] Failed to accept connection: {e}")
            traceback.print_exc()
            raise

    def disconnect(self, websocket: WebSocket, reason: Optional[str] = None, close_code: Optional[int] = None):
        """Remove a WebSocket connection with detailed logging"""
        disconnect_time = datetime.now()

        # Get connection info before removal
        conn_info = self.connection_info.get(websocket, {})
        connection_id = conn_info.get("connection_id", "unknown")
        connected_at = conn_info.get("connected_at")
        messages_sent = conn_info.get("messages_sent", 0)
        messages_received = conn_info.get("messages_received", 0)

        # Calculate connection duration
        duration = None
        if connected_at:
            duration = (disconnect_time - connected_at).total_seconds()

        # Interpret close code
        close_reason = self._interpret_close_code(close_code) if close_code else "Normal disconnect"

        # Log disconnection
        disconnect_entry = {
            "connection_id": connection_id,
            "disconnected_at": disconnect_time.isoformat(),
            "duration_seconds": duration,
            "messages_sent": messages_sent,
            "messages_received": messages_received,
            "close_code": close_code,
            "close_reason": close_reason,
            "reason": reason or "No reason provided"
        }
        self.disconnection_log.append(disconnect_entry)

        # Limit disconnection log size
        if len(self.disconnection_log) > self.max_disconnect_log:
            self.disconnection_log = self.disconnection_log[-self.max_disconnect_log:]

        # Remove connection
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_info:
            del self.connection_info[websocket]

        # Debug logging
        if self.debug_mode:
            print(f"[WS-DEBUG] ========== DISCONNECTION ==========")
            print(f"[WS-DEBUG] Connection ID: #{connection_id}")
            print(f"[WS-DEBUG] Duration: {duration:.2f}s" if duration else "[WS-DEBUG] Duration: unknown")
            print(f"[WS-DEBUG] Messages Sent: {messages_sent}")
            print(f"[WS-DEBUG] Messages Received: {messages_received}")
            print(f"[WS-DEBUG] Close Code: {close_code} ({close_reason})")
            print(f"[WS-DEBUG] Reason: {reason or 'None'}")
            print(f"[WS-DEBUG] Active Connections: {len(self.active_connections)}")
            print(f"[WS-DEBUG] ======================================")
        else:
            print(f"[WS] Client disconnected. Total connections: {len(self.active_connections)}")

    def _interpret_close_code(self, code: int) -> str:
        """Interpret WebSocket close codes"""
        close_codes = {
            1000: "Normal Closure",
            1001: "Going Away (browser navigating away)",
            1002: "Protocol Error",
            1003: "Unsupported Data",
            1005: "No Status Received",
            1006: "Abnormal Closure (no close frame)",
            1007: "Invalid Frame Payload Data",
            1008: "Policy Violation",
            1009: "Message Too Big",
            1010: "Mandatory Extension Missing",
            1011: "Internal Server Error",
            1012: "Service Restart",
            1013: "Try Again Later",
            1014: "Bad Gateway",
            1015: "TLS Handshake Failure"
        }
        return close_codes.get(code, f"Unknown Code ({code})")

    async def disconnect_all(self):
        """Disconnect all active connections"""
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except:
                pass
            self.disconnect(connection)

    def _update_activity(self, websocket: WebSocket, sent: bool = False, received: bool = False):
        """Update connection activity tracking"""
        if websocket in self.connection_info:
            self.connection_info[websocket]["last_activity"] = datetime.now()
            if sent:
                self.connection_info[websocket]["messages_sent"] += 1
            if received:
                self.connection_info[websocket]["messages_received"] += 1

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message)
            self._update_activity(websocket, sent=True)
        except Exception as e:
            conn_info = self.connection_info.get(websocket, {})
            connection_id = conn_info.get("connection_id", "unknown")
            if self.debug_mode:
                print(f"[WS-DEBUG] Error sending to connection #{connection_id}: {e}")
                traceback.print_exc()
            else:
                print(f"[WS-ERROR] Error sending message to client: {e}")
            self.disconnect(websocket, reason=f"Send error: {str(e)}")

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
                self._update_activity(connection, sent=True)
            except Exception as e:
                conn_info = self.connection_info.get(connection, {})
                connection_id = conn_info.get("connection_id", "unknown")
                if self.debug_mode:
                    print(f"[WS-DEBUG] Broadcast error to connection #{connection_id}: {e}")
                else:
                    print(f"[WS-ERROR] Error broadcasting to client: {e}")
                disconnected.append((connection, str(e)))

        # Remove disconnected clients
        for conn, error in disconnected:
            self.disconnect(conn, reason=f"Broadcast error: {error}")

    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcast JSON data to all connected clients"""
        message = json.dumps(data)
        await self.broadcast(message)

    def active_connections_count(self) -> int:
        """Get the count of active connections"""
        return len(self.active_connections)

    def _store_message(self, event_type: str, data: Any):
        """Store message in history for replay on reconnection"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.message_history.append(message)

        # Limit history size
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]

        # Update session state based on message type
        if event_type == "system_status":
            self.session_state.update({
                "running": data.get("running", False),
                "current_stage": data.get("current_stage"),
                "current_agent": data.get("current_agent"),
                "current_issue": data.get("current_issue"),
                "current_branch": data.get("current_branch"),
                "config": data.get("config"),
                "stats": data.get("stats", {}),
                "start_time": data.get("start_time")
            })

    async def _replay_history(self, websocket: WebSocket):
        """Replay stored message history to newly connected client"""
        if not self.message_history:
            print("[WS] No history to replay")
            # Send current session state even if no history
            await self._send_session_state(websocket)
            return

        print(f"[WS] Replaying {len(self.message_history)} messages to new client")

        # Send session restoration notification
        await self.send_personal_message(json.dumps({
            "type": "session_restore",
            "data": {
                "message": f"Restoring session with {len(self.message_history)} messages",
                "history_count": len(self.message_history)
            },
            "timestamp": datetime.now().isoformat()
        }), websocket)

        # Replay all stored messages
        for message in self.message_history:
            try:
                await websocket.send_text(json.dumps(self._encode_for_transport(message), ensure_ascii=False))
                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"[WS] Error replaying message: {e}")
                break

        print("[WS] History replay complete")

    def _encode_for_transport(self, data: Any) -> Any:
        """Encode data for WebSocket transport using FastAPI's jsonable_encoder"""
        try:
            return jsonable_encoder(data)
        except Exception as e:
            print(f"[WS-ERROR] Failed to encode data for transport: {e}")
            # Return simple string representation as fallback
            return {"error": "encoding_failed", "data": str(data)}

    async def _send_session_state(self, websocket: WebSocket):
        """Send current session state to client"""
        message = {
            "type": "system_status",
            "data": self.session_state,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_personal_message(json.dumps(message), websocket)
        print(f"[WS] Sent current system status to new connection: running={self.session_state['running']}")

    async def send_event(self, event_type: str, data: Any):
        """Send an event to all connected clients"""
        encoded_data = self._encode_for_transport(data)
        message = self._encode_for_transport({
            "type": event_type,
            "data": encoded_data,
            "timestamp": datetime.now().isoformat()
        })

        # Store message for history replay
        self._store_message(event_type, encoded_data)

        # Broadcast to all connected clients
        await self.broadcast_json(message)

    async def send_agent_output(self, agent: str, content: str, level: str = "info"):
        """Send agent output to all clients"""
        await self.send_event("agent_output", {
            "agent": agent,
            "content": content,
            "level": level
        })

    async def send_tool_use(self, agent: str, tool: str, input_data: Dict, output_data: Any = None, success: bool = True):
        """Send tool usage information to all clients"""
        await self.send_event("tool_use", {
            "agent": agent,
            "tool": tool,
            "input": input_data,
            "output": output_data,
            "success": success
        })

    async def send_pipeline_update(self, stage: str, status: str, details: Dict[str, Any] = None):
        """Send pipeline stage update to all clients"""
        await self.send_event("pipeline_update", {
            "stage": stage,
            "status": status,
            "details": details or {}
        })

    async def send_system_status(self, status: Dict[str, Any]):
        """Send system status update to all clients"""
        await self.send_event("system_status", status)

    async def send_issue_update(self, issue_id: int, status: str, details: Dict[str, Any] = None):
        """Send issue processing update to all clients"""
        # Update session state based on issue status
        if status == "completed":
            if issue_id not in self.session_state["completed_issues"]:
                self.session_state["completed_issues"].append(issue_id)
                print(f"[WS-STATE] Tracking completed issue #{issue_id}")
        elif status == "failed":
            if issue_id not in self.session_state["failed_issues"]:
                self.session_state["failed_issues"].append(issue_id)
                print(f"[WS-STATE] Tracking failed issue #{issue_id}")

        await self.send_event("issue_update", {
            "issue_id": issue_id,
            "status": status,
            "details": details or {}
        })

    async def send_error(self, error: str, details: Dict[str, Any] = None):
        """Send error message to all clients"""
        await self.send_event("error", {
            "message": error,
            "details": details or {}
        })

    async def send_success(self, message: str, details: Dict[str, Any] = None):
        """Send success message to all clients"""
        await self.send_event("success", {
            "message": message,
            "details": details or {}
        })

    async def send_tech_stack(self, tech_stack: Dict[str, Any]):
        """Send detected tech stack to all clients"""
        await self.send_event("tech_stack_detected", {
            "language": tech_stack.get("backend", "unknown"),
            "framework": tech_stack.get("frontend", "none"),
            "testing": tech_stack.get("testing", "unknown")
        })

    async def send_mcp_log(self, message: str, level: str = "info"):
        """Send MCP server log to all clients"""
        await self.send_event("mcp_log", {
            "message": message,
            "level": level
        })

    def clear_session(self):
        """Clear session history when system fully stops"""
        print("[WS] Clearing session history")
        self.message_history.clear()
        self.session_state = {
            "running": False,
            "current_stage": None,
            "current_agent": None,
            "current_issue": None,
            "current_branch": None,
            "config": None,
            "stats": {},
            "start_time": None,
            "completed_issues": [],
            "failed_issues": []
        }

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            "history_count": len(self.message_history),
            "active_connections": len(self.active_connections),
            "total_connections": self.connection_counter,
            "session_state": self.session_state,
            "debug_mode": self.debug_mode
        }

    def get_connection_diagnostics(self) -> Dict[str, Any]:
        """Get detailed connection diagnostics for debugging"""
        # Get active connection details
        active_details = []
        for ws in self.active_connections:
            info = self.connection_info.get(ws, {})
            connected_at = info.get("connected_at")
            duration = (datetime.now() - connected_at).total_seconds() if connected_at else 0

            active_details.append({
                "connection_id": info.get("connection_id", "unknown"),
                "client": info.get("client_state", "unknown"),
                "connected_for_seconds": round(duration, 2),
                "messages_sent": info.get("messages_sent", 0),
                "messages_received": info.get("messages_received", 0),
                "last_activity": info.get("last_activity").isoformat() if info.get("last_activity") else None
            })

        # Get recent disconnections
        recent_disconnects = self.disconnection_log[-10:]  # Last 10 disconnections

        return {
            "debug_mode": self.debug_mode,
            "total_connections_since_start": self.connection_counter,
            "active_connections_count": len(self.active_connections),
            "active_connections": active_details,
            "recent_disconnections": recent_disconnects,
            "message_history_size": len(self.message_history),
            "session_state": self.session_state
        }

    def get_disconnection_summary(self) -> Dict[str, Any]:
        """Get summary of disconnection patterns"""
        if not self.disconnection_log:
            return {"message": "No disconnections recorded"}

        # Count close codes
        close_code_counts = {}
        total_duration = 0
        count = 0

        for entry in self.disconnection_log:
            code = entry.get("close_code", "unknown")
            close_code_counts[code] = close_code_counts.get(code, 0) + 1

            if entry.get("duration_seconds"):
                total_duration += entry["duration_seconds"]
                count += 1

        avg_duration = total_duration / count if count > 0 else 0

        return {
            "total_disconnections": len(self.disconnection_log),
            "average_connection_duration_seconds": round(avg_duration, 2),
            "close_code_distribution": close_code_counts,
            "most_recent": self.disconnection_log[-1] if self.disconnection_log else None
        }

    async def start_keepalive(self):
        """
        Start the keepalive background task.

        IMPORTANT: Runs in the main event loop but designed to minimize
        interference with other async operations (like MCP client calls).
        The keepalive uses exponential intervals and error isolation.
        """
        if self._keepalive_running:
            print("[WS-KEEPALIVE] Keepalive already running")
            return

        self._keepalive_running = True
        self.keepalive_task = asyncio.create_task(self._keepalive_loop())
        print(f"[WS-KEEPALIVE] Started with {self.keepalive_interval}s interval")
        print(f"[WS-KEEPALIVE] Using error-isolated ping mechanism to prevent TaskGroup interference")

    async def stop_keepalive(self):
        """Stop the keepalive background task"""
        self._keepalive_running = False
        if self.keepalive_task:
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass
            print("[WS-KEEPALIVE] Stopped")

    async def _keepalive_loop(self):
        """
        Background task that sends periodic pings to keep connections alive.

        Uses asyncio.shield() for each ping operation to prevent interference
        with other tasks in the event loop (especially MCP client operations).
        """
        print(f"[WS-KEEPALIVE] Loop started - sending pings every {self.keepalive_interval}s")
        print(f"[WS-KEEPALIVE] Using shielded operations to prevent TaskGroup interference")

        try:
            while self._keepalive_running:
                await asyncio.sleep(self.keepalive_interval)

                if not self.active_connections:
                    continue

                # Send ping to all active connections with error isolation
                disconnected = []
                for connection in self.active_connections[:]:  # Copy list to avoid modification during iteration
                    try:
                        # Shield the ping operation from external cancellation
                        # This prevents TaskGroup exceptions in other parts of the system
                        # from interfering with WebSocket keepalive
                        await asyncio.shield(
                            connection.send_json({
                                "type": "keepalive",
                                "timestamp": datetime.now().isoformat()
                            })
                        )

                        # Update last ping time
                        if connection in self.connection_info:
                            self.connection_info[connection]["last_ping"] = datetime.now()

                    except asyncio.CancelledError:
                        # Keepalive task itself is being cancelled (e.g., server shutdown)
                        # Don't mark connection as failed, just stop
                        print(f"[WS-KEEPALIVE] Keepalive cancelled during ping")
                        raise

                    except Exception as e:
                        # Individual ping failed - mark connection as dead
                        conn_info = self.connection_info.get(connection, {})
                        connection_id = conn_info.get("connection_id", "unknown")
                        print(f"[WS-KEEPALIVE] Ping failed for connection #{connection_id}: {e}")
                        disconnected.append((connection, str(e)))

                # Remove dead connections
                for conn, error in disconnected:
                    self.disconnect(conn, reason=f"Keepalive ping failed: {error}")

                if self.debug_mode and self.active_connections:
                    print(f"[WS-KEEPALIVE] Sent keepalive to {len(self.active_connections)} connections")

        except asyncio.CancelledError:
            print("[WS-KEEPALIVE] Loop cancelled")
        except Exception as e:
            print(f"[WS-KEEPALIVE] Loop error: {e}")
            traceback.print_exc()


# Global connection manager instance
ws_manager = ConnectionManager()
