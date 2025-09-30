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
    """Captures stdout/stderr output and sends it via WebSocket - OPTIMIZED"""

    def __init__(self, ws_manager, agent_name: str):
        self.ws_manager = ws_manager
        self.agent_name = agent_name
        self.original_stdout = None
        self.original_stderr = None
        self.sentence_buffer = ""  # Buffer to accumulate text
        self.batch_buffer = []  # Batch multiple messages
        self.write_count = 0  # Track writes for time check throttling
        self.last_send_time = time.time()
        self.send_interval = 0.2  # Send every 0.2 seconds for better responsiveness
        self.batch_size = 2  # Send every 2 messages (reduced for visibility)

    def write(self, text: str):
        """Write method for stdout/stderr replacement - OPTIMIZED"""
        # Write to original stdout
        if self.original_stdout:
            self.original_stdout.write(text)

        # Fast filter for unwanted messages (single check)
        if "Session termination failed" in text:
            return

        # Accumulate text
        self.sentence_buffer += text
        self.write_count += 1

        # CRITICAL: Immediate send for tool calls and important progress markers
        important_markers = [
            "[TOOL]", "[MCP]", "[DONE]", "Reading:", "Creating:", "Updating:",
            "list_issues", "get_file_contents", "get_repo_tree", "create_or_update_file",
            "list_branches", "list_merge_requests", "get_project", "get_issue"
        ]
        is_important = any(marker in text for marker in important_markers)

        if is_important:
            # Force immediate send for visibility
            if self.sentence_buffer.strip():
                self._batch_and_send()
                self._send_batch()  # Force immediate WebSocket send
            return

        # Simplified send logic - prioritize responsiveness
        should_send = False
        buffer_len = len(self.sentence_buffer)

        if '\n' in text:  # Immediate send on newline
            should_send = True
        elif buffer_len >= 100:  # Force send on moderate buffer
            should_send = True
        else:
            # Check time periodically (every 20 writes for balance)
            if self.write_count % 20 == 0:
                current_time = time.time()
                if current_time - self.last_send_time > self.send_interval:
                    should_send = True
                    self.last_send_time = current_time

        if should_send and self.sentence_buffer.strip():
            self._batch_and_send()

    def flush(self):
        """Flush method for stdout/stderr replacement"""
        if self.original_stdout:
            self.original_stdout.flush()
        # Force send remaining buffer
        if self.sentence_buffer.strip():
            self._batch_and_send()
        # Send any remaining batched messages
        if self.batch_buffer:
            self._send_batch()

    def _batch_and_send(self):
        """Add to batch and send if batch is full - OPTIMIZED"""
        if self.sentence_buffer.strip():
            self.batch_buffer.append(self.sentence_buffer)
            self.sentence_buffer = ""

            # Send batch if full
            if len(self.batch_buffer) >= self.batch_size:
                self._send_batch()

    def _send_batch(self):
        """Send batched messages via WebSocket - NON-BLOCKING"""
        if not self.batch_buffer:
            return

        # Join all messages with newlines
        combined_output = "\n".join(self.batch_buffer)
        self.batch_buffer = []

        # Create fire-and-forget task (async-safe)
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # Schedule the coroutine to run in the event loop
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.send_agent_output(
                    self.agent_name,
                    combined_output,
                    "info"
                ),
                loop
            )
        except RuntimeError:
            # No event loop - save for later or write to original stdout
            if self.original_stdout:
                self.original_stdout.write(f"[{self.agent_name}] {combined_output}\n")

    def __enter__(self):
        """Start capturing output"""
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing output"""
        # Send any remaining output (uses flush which handles both buffers)
        self.flush()

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

        # Send agent start event (async-safe)
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.send_event("agent_start", {
                    "agent": agent_name,
                    "timestamp": datetime.now().isoformat()
                }),
                loop
            )
        except RuntimeError:
            # No event loop - skip WebSocket send
            pass

        # Capture output
        capture = OutputCapture(self.ws_manager, agent_name)

        try:
            with capture:
                yield
        finally:
            # Calculate duration
            duration = (datetime.now() - self.agent_start_times[agent_name]).total_seconds()

            # Send agent complete event (async-safe)
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(
                    self.ws_manager.send_event("agent_complete", {
                        "agent": agent_name,
                        "duration": duration,
                        "timestamp": datetime.now().isoformat()
                    }),
                    loop
                )
            except RuntimeError:
                # No event loop - skip WebSocket send
                pass

    def record_output(self, agent_name: str, output: str, level: str = "info"):
        """Record agent output"""
        if agent_name not in self.agent_outputs:
            self.agent_outputs[agent_name] = []

        self.agent_outputs[agent_name].append({
            "timestamp": datetime.now(),
            "content": output,
            "level": level
        })

        # Send via WebSocket (async-safe)
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.send_agent_output(agent_name, output, level),
                loop
            )
        except RuntimeError:
            # No event loop - skip WebSocket send
            pass

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

        # Send tool start event (async-safe)
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.send_event("tool_start", {
                    "agent": agent,
                    "tool": tool,
                    "input": input_data,
                    "timestamp": datetime.now().isoformat()
                }),
                loop
            )
        except RuntimeError:
            # No event loop - skip WebSocket send
            pass

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

        # Send tool end event (async-safe)
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.send_event("tool_end", {
                    "agent": agent,
                    "tool": tool,
                    "output": str(output) if output else None,
                    "duration_ms": duration_ms,
                    "success": success,
                    "timestamp": datetime.now().isoformat()
                }),
                loop
            )
        except RuntimeError:
            # No event loop - skip WebSocket send
            pass

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