"""
WebSocket connection manager for real-time updates
"""

from typing import List, Dict, Any
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections for real-time communication"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = {
            "connected_at": datetime.now(),
            "last_ping": datetime.now()
        }
        print(f"[WS] Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_info:
            del self.connection_info[websocket]
        print(f"[WS] Client disconnected. Total connections: {len(self.active_connections)}")

    async def disconnect_all(self):
        """Disconnect all active connections"""
        for connection in self.active_connections[:]:
            try:
                await connection.close()
            except:
                pass
            self.disconnect(connection)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending message to client: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Broadcast a message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcast JSON data to all connected clients"""
        message = json.dumps(data)
        await self.broadcast(message)

    def active_connections_count(self) -> int:
        """Get the count of active connections"""
        return len(self.active_connections)

    async def send_event(self, event_type: str, data: Any):
        """Send an event to all connected clients"""
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
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


# Global connection manager instance
ws_manager = ConnectionManager()