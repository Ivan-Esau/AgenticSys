"""
Stream management for agent output.
Handles token streaming and progress display.
"""

from typing import Optional, Dict, Any, AsyncGenerator


class StreamManager:
    """
    Manages streaming output and progress display for agents.
    Handles both token streaming and tool execution progress.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.final_content = None
    
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
                
                # Handle token streaming
                elif kind == "on_chat_model_stream":
                    if show_tokens:
                        self._handle_token_stream(data)
                
                # Capture final output
                elif kind == "on_chat_model_end":
                    final_content = self._extract_final_content(data)
                    
        except Exception as e:
            # Silently catch streaming errors - will fall back to non-streaming
            pass
        
        return final_content
    
    def _handle_tool_start(self, data: Dict[str, Any]) -> None:
        """Handle tool start events."""
        tool_name = data.get("name", "")
        tool_input = data.get("input", {})
        
        if tool_name:
            print(f"  [TOOL] {tool_name}")
            
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
            # Show completion status for specific tools
            if tool_name in ['create_file', 'update_file']:
                print(f"    [DONE] File operation completed")
            elif tool_name == 'create_branch':
                print(f"    [DONE] Branch created")
            elif tool_name == 'create_merge_request':
                print(f"    [DONE] Merge request created")
            elif tool_name == 'merge_merge_request':
                print(f"    [DONE] Merge request merged!")
            elif tool_name in ['get_project', 'get_repository_tree', 'list_issues']:
                print(f"    [DONE] Data retrieved")
    
    def _handle_token_stream(self, data: Dict[str, Any]) -> None:
        """Handle token streaming events."""
        chunk = data.get("chunk", {})
        
        if hasattr(chunk, "content"):
            content = chunk.content
        else:
            content = chunk.get("content") if isinstance(chunk, dict) else None
        
        if content:
            print(content, end="", flush=True)
    
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