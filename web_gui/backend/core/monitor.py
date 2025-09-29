"""
Monitoring utilities for capturing agent outputs and tool usage
"""

import sys
import io
import time
import asyncio
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime
import threading


class OutputCapture:
    """Captures stdout/stderr output and sends it via WebSocket"""

    def __init__(self, ws_manager, agent_name: str):
        self.ws_manager = ws_manager
        self.agent_name = agent_name
        self.original_stdout = None
        self.original_stderr = None
        self.capture_buffer = io.StringIO()
        self.last_send_time = time.time()
        self.send_interval = 0.5  # Send updates every 0.5 seconds
        self.min_chars_threshold = 100  # Minimum characters before sending
        self.sentence_buffer = ""  # Buffer to accumulate text until complete sentences

    def write(self, text: str):
        """Write method for stdout/stderr replacement"""
        # Write to original stdout
        if self.original_stdout:
            self.original_stdout.write(text)

        # Add text to sentence buffer
        self.sentence_buffer += text
        current_time = time.time()

        # Look for natural break points
        break_points = ['.', '!', '?', '\n', ':', ';']
        should_send = False

        # Send if we have natural break points and some content
        if any(bp in self.sentence_buffer for bp in break_points):
            # More lenient: send if we have any break point and reasonable length
            if len(self.sentence_buffer.strip()) >= 20:
                should_send = True

        # Also send if buffer is getting long or time threshold reached
        if (len(self.sentence_buffer) >= 50 or  # Lower threshold
            (current_time - self.last_send_time > self.send_interval) or
            len(self.sentence_buffer) >= 200):  # Force send if very long
            should_send = True

        # Emergency send if nothing sent for too long
        if current_time - self.last_send_time > 2.0:  # 2 second maximum delay
            should_send = True

        if should_send and self.sentence_buffer.strip():
            self._send_sentence_buffer()
            self.last_send_time = current_time

    def flush(self):
        """Flush method for stdout/stderr replacement"""
        if self.original_stdout:
            self.original_stdout.flush()
        self._send_sentence_buffer()

    def _send_sentence_buffer(self):
        """Send accumulated sentence buffer via WebSocket"""
        if self.sentence_buffer.strip():
            # Create async task to send via WebSocket
            asyncio.create_task(
                self.ws_manager.send_agent_output(
                    self.agent_name,
                    self.sentence_buffer,
                    "info"
                )
            )
            # Clear sentence buffer
            self.sentence_buffer = ""

    def _send_captured_output(self):
        """Send captured output via WebSocket (legacy method)"""
        output = self.capture_buffer.getvalue()
        if output:
            # Create async task to send via WebSocket
            asyncio.create_task(
                self.ws_manager.send_agent_output(
                    self.agent_name,
                    output,
                    "info"
                )
            )
            # Clear buffer
            self.capture_buffer = io.StringIO()

    def __enter__(self):
        """Start capturing output"""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing output"""
        # Send any remaining output
        self._send_sentence_buffer()

        # Restore original stdout/stderr
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr


class AgentMonitor:
    """Monitors agent execution and captures output"""

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self.agent_start_times: Dict[str, datetime] = {}
        self.agent_outputs: Dict[str, list] = {}

    @contextmanager
    def capture_output(self, agent_name: str):
        """Context manager to capture agent output"""
        # Record start time
        self.agent_start_times[agent_name] = datetime.now()

        # Send agent start event
        asyncio.create_task(
            self.ws_manager.send_event("agent_start", {
                "agent": agent_name,
                "timestamp": datetime.now().isoformat()
            })
        )

        # Capture output
        capture = OutputCapture(self.ws_manager, agent_name)

        try:
            with capture:
                yield
        finally:
            # Calculate duration
            duration = (datetime.now() - self.agent_start_times[agent_name]).total_seconds()

            # Send agent complete event
            asyncio.create_task(
                self.ws_manager.send_event("agent_complete", {
                    "agent": agent_name,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                })
            )

    def record_output(self, agent_name: str, output: str, level: str = "info"):
        """Record agent output"""
        if agent_name not in self.agent_outputs:
            self.agent_outputs[agent_name] = []

        self.agent_outputs[agent_name].append({
            "timestamp": datetime.now(),
            "content": output,
            "level": level
        })

        # Send via WebSocket
        asyncio.create_task(
            self.ws_manager.send_agent_output(agent_name, output, level)
        )

    def get_agent_outputs(self, agent_name: str) -> list:
        """Get all outputs for a specific agent"""
        return self.agent_outputs.get(agent_name, [])

    def clear_agent_outputs(self, agent_name: str):
        """Clear outputs for a specific agent"""
        if agent_name in self.agent_outputs:
            self.agent_outputs[agent_name] = []


class ToolMonitor:
    """Monitors tool usage by agents"""

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self.tool_calls: Dict[str, list] = {}
        self.tool_timings: Dict[str, float] = {}

    def record_tool_start(self, agent: str, tool: str, input_data: Dict[str, Any]):
        """Record the start of a tool call"""
        key = f"{agent}:{tool}:{time.time()}"
        self.tool_timings[key] = time.time()

        # Send tool start event
        asyncio.create_task(
            self.ws_manager.send_event("tool_start", {
                "agent": agent,
                "tool": tool,
                "input": input_data,
                "timestamp": datetime.now().isoformat()
            })
        )

        return key

    def record_tool_end(self, key: str, output: Any = None, success: bool = True):
        """Record the end of a tool call"""
        if key not in self.tool_timings:
            return

        start_time = self.tool_timings[key]
        duration_ms = int((time.time() - start_time) * 1000)

        parts = key.split(":", 2)
        agent = parts[0]
        tool = parts[1]

        # Store tool call record
        if agent not in self.tool_calls:
            self.tool_calls[agent] = []

        self.tool_calls[agent].append({
            "tool": tool,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.now()
        })

        # Send tool end event
        asyncio.create_task(
            self.ws_manager.send_event("tool_end", {
                "agent": agent,
                "tool": tool,
                "output": str(output) if output else None,
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })
        )

        # Clean up timing record
        del self.tool_timings[key]

    def get_tool_stats(self, agent: str = None) -> Dict[str, Any]:
        """Get tool usage statistics"""
        if agent:
            calls = self.tool_calls.get(agent, [])
        else:
            calls = []
            for agent_calls in self.tool_calls.values():
                calls.extend(agent_calls)

        if not calls:
            return {
                "total_calls": 0,
                "success_rate": 0,
                "avg_duration_ms": 0
            }

        total = len(calls)
        successful = sum(1 for c in calls if c["success"])
        avg_duration = sum(c["duration_ms"] for c in calls) / total

        return {
            "total_calls": total,
            "success_rate": (successful / total) * 100,
            "avg_duration_ms": avg_duration,
            "tools_used": list(set(c["tool"] for c in calls))
        }


class ToolWrapper:
    """Wraps MCP tools to monitor their usage"""

    def __init__(self, original_tool, tool_monitor: ToolMonitor, agent_name: str):
        self.original_tool = original_tool
        self.tool_monitor = tool_monitor
        self.agent_name = agent_name
        self.tool_name = getattr(original_tool, "name", str(original_tool))

    async def __call__(self, *args, **kwargs):
        """Execute the tool with monitoring"""
        # Record tool start
        key = self.tool_monitor.record_tool_start(
            self.agent_name,
            self.tool_name,
            {"args": args, "kwargs": kwargs}
        )

        try:
            # Execute original tool
            result = await self.original_tool(*args, **kwargs)

            # Record success
            self.tool_monitor.record_tool_end(key, result, True)

            return result

        except Exception as e:
            # Record failure
            self.tool_monitor.record_tool_end(key, str(e), False)
            raise


def wrap_tools_for_monitoring(tools: list, tool_monitor: ToolMonitor, agent_name: str) -> list:
    """Wrap a list of tools with monitoring"""
    wrapped_tools = []
    for tool in tools:
        wrapped = ToolWrapper(tool, tool_monitor, agent_name)
        wrapped_tools.append(wrapped)
    return wrapped_tools