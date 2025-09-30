"""
Stream management for agent output.
Handles token streaming and progress display.
"""

from typing import Optional, Dict, Any, AsyncGenerator
import time


class StreamManager:
    """
    Manages streaming output and progress display for agents.
    Handles both token streaming and tool execution progress.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.final_content = None
        self.sentence_buffer = ""  # Buffer to accumulate tokens into sentences
        self.last_flush_time = time.time()
        self.flush_interval = 0.5  # Flush every 0.5 seconds (reduced frequency)
        self.token_count = 0  # Track tokens for time check throttling
    
    async def handle_stream_events(
        self,
        stream: AsyncGenerator,
        show_tokens: bool = True
    ) -> Optional[str]:
        """
        Handle streaming events from the agent and display progress.

        Args:
            stream: Async generator of stream events
            show_tokens: Whether to show token streaming

        Returns:
            Final content from the stream
        """
        final_content = None

        try:
            async for event in stream:
                kind = event.get("event", "")
                data = event.get("data", {})

                # Handle tool execution progress
                if kind == "on_tool_start":
                    self._handle_tool_start(data)
                elif kind == "on_tool_end":
                    self._handle_tool_end(data)
                elif kind == "on_tool_error":
                    self._handle_tool_error(data)

                # Handle token streaming
                elif kind == "on_chat_model_stream":
                    if show_tokens:
                        self._handle_token_stream(data)

                # Capture final output
                elif kind == "on_chat_model_end":
                    # Flush any remaining buffered content
                    if show_tokens:
                        self._flush_remaining_buffer()
                    final_content = self._extract_final_content(data)

        except Exception as e:
            # Log streaming errors and let the agent fall back to non-streaming
            print(f"[STREAM] Stream error: {e}")
            raise
        finally:
            # Always flush remaining buffer when stream ends
            self._flush_remaining_buffer()

        return final_content
    
    def _handle_tool_start(self, data: Dict[str, Any]) -> None:
        """Handle tool start events."""
        tool_name = data.get("name", "")
        tool_input = data.get("input", {})

        if tool_name:
            # Flush any remaining sentence buffer before showing tool usage
            self._flush_remaining_buffer()

            print(f"\n  [TOOL] {tool_name}")

            # Show specific context for certain tools
            if tool_name == 'get_file_contents':
                file_path = tool_input.get('file', '')
                print(f"    Reading: {file_path}")
            elif tool_name == 'create_file':
                file_path = tool_input.get('file', '')
                print(f"    Creating: {file_path}")
            elif tool_name == 'update_file':
                file_path = tool_input.get('file', '')
                print(f"    Updating: {file_path}")
    
    def _handle_tool_end(self, data: Dict[str, Any]) -> None:
        """Handle tool end events."""
        tool_name = data.get("name", "")

        if tool_name:
            # Check for errors first
            output = data.get("output", {})
            error = None

            # Extract error from different possible formats
            if isinstance(output, dict):
                error = output.get("error") or output.get("message")
            elif isinstance(output, str) and ("error" in output.lower() or "failed" in output.lower()):
                error = output

            # Show error if present
            if error:
                print(f"    [FAIL] {tool_name}: {error}")
                return

            # Show completion status for specific tools
            if tool_name in ['create_file', 'update_file', 'create_or_update_file']:
                print(f"    [DONE] File operation completed")
            elif tool_name == 'create_branch':
                print(f"    [DONE] Branch created")
            elif tool_name == 'create_merge_request':
                print(f"    [DONE] Merge request created")
            elif tool_name == 'merge_merge_request':
                print(f"    [DONE] Merge request merged!")
            elif tool_name in ['get_project', 'get_repository_tree', 'list_issues', 'get_file_contents', 'list_branches', 'list_merge_requests']:
                print(f"    [DONE] {tool_name} completed")

    def _handle_tool_error(self, data: Dict[str, Any]) -> None:
        """Handle tool error events."""
        tool_name = data.get("name", "")
        error = data.get("error", "Unknown error")

        # Flush any buffered output before showing error
        self._flush_remaining_buffer()

        print(f"    [ERROR] {tool_name} failed: {error}")

    def _handle_token_stream(self, data: Dict[str, Any]) -> None:
        """Handle token streaming events with sentence buffering - OPTIMIZED."""
        chunk = data.get("chunk", {})

        if hasattr(chunk, "content"):
            content = chunk.content
        else:
            content = chunk.get("content") if isinstance(chunk, dict) else None

        if content:
            # Filter out verbose JSON blocks and show only important updates
            if "```json" in content or '"issues": [' in content or '"implementation_steps"' in content:
                # Don't stream verbose JSON content, just show progress indicator
                if not hasattr(self, '_json_suppressed'):
                    print("[Generating orchestration plan...]", end="", flush=True)
                    self._json_suppressed = True
            else:
                # Add token to sentence buffer
                self.sentence_buffer += content
                self.token_count += 1

                # Simplified flush logic for better responsiveness
                should_flush = False
                buffer_len = len(self.sentence_buffer)

                if '\n' in content:  # Immediate flush on newline
                    should_flush = True
                elif buffer_len >= 100:  # Force flush on moderate buffer
                    should_flush = True
                else:
                    # Check time periodically (every 10 tokens to reduce syscalls but stay responsive)
                    if self.token_count % 10 == 0:
                        current_time = time.time()
                        if current_time - self.last_flush_time > self.flush_interval:
                            should_flush = True
                            self.last_flush_time = current_time

                # Flush the buffer
                if should_flush and self.sentence_buffer.strip():
                    print(self.sentence_buffer, end="", flush=True)
                    self.sentence_buffer = ""
                    self.last_flush_time = time.time()

    def _flush_remaining_buffer(self) -> None:
        """Flush any remaining content in the sentence buffer."""
        if self.sentence_buffer.strip():
            print(self.sentence_buffer, end="", flush=True)
            self.sentence_buffer = ""
    
    def _extract_final_content(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract final content from model end event."""
        output = data.get("output", {})
        
        # Try different ways to extract content
        if hasattr(output, "content"):
            return output.content
        elif isinstance(output, dict):
            # Try generations path
            gens = output.get("generations", [])
            if gens and len(gens) > 0 and len(gens[0]) > 0:
                msg = gens[0][0]
                if hasattr(msg, "message"):
                    return msg.message.content if hasattr(msg.message, "content") else str(msg.message)
                elif isinstance(msg, dict) and "message" in msg:
                    return msg["message"].get("content", str(msg["message"]))
        
        return None
    
    def show_agent_header(self, show_tokens: bool = True) -> None:
        """Show agent start header."""
        if show_tokens:
            print(f"\n{'=' * 60}")
            print(f"[{self.agent_name.upper()}] Starting...")
            print(f"{'=' * 60}")