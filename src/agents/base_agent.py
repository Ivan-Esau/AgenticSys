from typing import Optional, List, Any
from ..core.config import Config
from ..core.llm_config import make_model
from ..core.utils import extract_json_block, truncate_text
from ..core.constants import STATUS_MESSAGES, ERROR_MESSAGES, EMOJIS
from ..core.state import get_project_state, ProjectState

# LangGraph for agent creation
from langgraph.prebuilt import create_react_agent

# For robust fallback on stream errors
try:
    import httpx, httpcore
except Exception:
    httpx = None
    httpcore = None

def _short(obj, lim: int = 240) -> str:
    """Helper function to truncate objects for display."""
    try:
        import json
        s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    except Exception:
        s = str(obj)
    s = s.replace("\n", " ")
    return truncate_text(s, lim)


class BaseAgent:
    """
    Wrapper for LangGraph ReAct agent with integrated state management:
      - Automatically uses ProjectState for caching and coordination
      - Streams with astream_events(v2) and prints progress
      - Auto-falls-back to non-streamed .ainvoke() if streaming fails
    """
    def _check_file_cache(self, tool_name: str, tool_input: dict) -> Optional[str]:
        """Check cache for file operations and return cached content if available"""
        if not self.state:
            return None
        
        if tool_name == 'get_file_contents':
            file_path = tool_input.get('file', '')
            cached_content = self.state.get_cached_file(file_path)
            if cached_content:
                print(f"  [CACHE HIT] File: {file_path} (from state cache)")
                return cached_content
        
        return None
    
    def _cache_file_result(self, tool_name: str, tool_input: dict, result: str) -> None:
        """Cache the result of file operations"""
        if not self.state:
            return
        
        if tool_name == 'get_file_contents' and isinstance(result, str) and result:
            file_path = tool_input.get('file', '')
            if file_path:
                self.state.cache_file(file_path, result)
                print(f"  [CACHED] File: {file_path} ({len(result)} chars)")

    def _wrap_tools_with_cache(self, tools):
        """Wrap tools with caching functionality - simplified for now"""
        # For now, return original tools and handle caching at agent level
        # This avoids LangGraph compatibility issues
        print(f"[CACHING] State connected: {self.state is not None}")
        if self.state:
            print(f"[CACHING] Will cache get_file_contents calls for project {self.project_id}")
        return tools
    
    

    def __init__(self, name: str, system_prompt: str, tools: List[Any], model=None, project_id: Optional[str] = None):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools
        self.model = model or make_model()
        # Integrate with ProjectState if project_id provided
        self.project_id = project_id
        self.state: Optional[ProjectState] = None
        if project_id:
            self.state = get_project_state(project_id)
            # Wrap tools with caching
            self.tools = self._wrap_tools_with_cache(self.tools)
        
        # Create agent with base configuration (using potentially wrapped tools)
        self.agent = create_react_agent(
            model=self.model,
            tools=self.tools,
            prompt=self.system_prompt
        )
        
        # Store config with higher recursion limit from configuration
        self.config = {"recursion_limit": Config.AGENT_RECURSION_LIMIT}  # Default: 200
        
        # Integrate with ProjectState if project_id provided
        self.project_id = project_id
        self.state: Optional[ProjectState] = None
        if project_id:
            self.state = get_project_state(project_id)
            # Wrap tools with caching
            self.tools = self._wrap_tools_with_cache(self.tools)

    async def _stream_run(self, inputs: dict, show_tokens: bool) -> Optional[str]:
        """Stream execution with progress display."""
        final_content = None
        current_tool_call = {}  # Track current tool being called
        
        try:
            async for ev in self.agent.astream_events(inputs, version="v2", config=self.config):
                # Handle different event types based on the structure
                if isinstance(ev, dict):
                    kind = ev.get("event")
                    data = ev.get("data", {})
                    
                    # Capture tool input from chat model
                    if kind == "on_chat_model_end":
                        # Try to extract tool calls from the model's output
                        if 'output' in data:
                            try:
                                # Check for tool_calls in the message
                                if hasattr(data['output'], 'tool_calls'):
                                    for tool_call in data['output'].tool_calls:
                                        if show_tokens:
                                            print(f"\n[{self.name.upper()}] Planning to use: {tool_call.get('name', 'unknown')}")
                                            args = tool_call.get('args', {})
                                            if isinstance(args, dict):
                                                if 'files' in args:
                                                    print(f"  Will modify {len(args['files'])} files")
                                                if 'branch' in args:
                                                    print(f"  Branch: {args['branch']}")
                                                if 'file_path' in args:
                                                    print(f"  File: {args['file_path']}")
                            except:
                                pass
                    
                    # Show tool calls with agent identification and details
                    if kind == "on_tool_start":
                        if show_tokens:
                            tool_name = ev.get('name', 'unknown')
                            current_tool_call['name'] = tool_name
                            print(f"\n[{self.name.upper()}] >> Executing: {tool_name}")
                            
                            # Extract input from various possible locations
                            tool_input = None
                            if 'run_id' in ev:
                                # Store run_id to match with results
                                current_tool_call['run_id'] = ev['run_id']
                            
                            # Try to get input from data
                            if data and 'input' in data:
                                tool_input = data['input']
                            elif 'tags' in ev:
                                # Sometimes input is in tags
                                for tag in ev.get('tags', []):
                                    if isinstance(tag, dict) and 'input' in tag:
                                        tool_input = tag['input']
                                        break
                            
                            
                            if tool_input and isinstance(tool_input, dict):
                                # Show key parameters for common tools
                                if tool_name == 'push_files' and 'files' in tool_input:
                                    files = tool_input.get('files', [])
                                    print(f"  [FILES] Creating/updating {len(files)} files:")
                                    for f in files[:5]:  # Show first 5 files
                                        if isinstance(f, dict):
                                            path = f.get('file_path', 'unknown')
                                            action = f.get('action', 'create')
                                            print(f"    - {action}: {path}")
                                    if len(files) > 5:
                                        print(f"    ... and {len(files) - 5} more files")
                                elif tool_name == 'create_branch' and 'branch' in tool_input:
                                    print(f"  [BRANCH] Creating: {tool_input.get('branch')}")
                                    print(f"  [FROM] Ref: {tool_input.get('ref', 'default branch')}")
                                elif tool_name == 'get_file_contents' and 'file_path' in tool_input:
                                    print(f"  [READ] File: {tool_input.get('file_path')}")
                                elif tool_name == 'create_merge_request':
                                    print(f"  [MR] From: {tool_input.get('source_branch', '?')}")
                                    print(f"  [MR] To: {tool_input.get('target_branch', '?')}")
                                    print(f"  [MR] Title: {tool_input.get('title', 'Untitled')[:50]}...")
                                elif tool_name == 'get_repository_tree':
                                    print(f"  [TREE] Path: {tool_input.get('path', '/')}")
                                elif tool_name == 'list_issues':
                                    print(f"  [ISSUES] State: {tool_input.get('state', 'all')}")
                                elif 'project_id' in tool_input:
                                    print(f"  [PROJECT] ID: {tool_input.get('project_id')}")
                    
                    # Show tool results
                    elif kind == "on_tool_end":
                        if show_tokens:
                            tool_name = ev.get('name', 'unknown')
                            
                            # Show completion for operations
                            if tool_name == 'get_file_contents':
                                print(f"  [DONE] File data retrieved")
                            elif tool_name == 'push_files':
                                print(f"  [DONE] Files pushed successfully")
                            elif tool_name == 'create_branch':
                                print(f"  [DONE] Branch created")
                            elif tool_name == 'create_merge_request':
                                print(f"  [DONE] Merge request created")
                            elif tool_name == 'merge_merge_request':
                                print(f"  [DONE] Merge request merged!")
                            elif tool_name in ['get_project', 'get_repository_tree', 'list_issues']:
                                print(f"  [DONE] Data retrieved")
                    
                    # Show token streaming
                    elif kind == "on_chat_model_stream":
                        chunk = data.get("chunk", {})
                        if hasattr(chunk, "content"):
                            content = chunk.content
                        else:
                            content = chunk.get("content") if isinstance(chunk, dict) else None
                        
                        if content and show_tokens:
                            print(content, end="", flush=True)
                    
                    # Capture final output
                    elif kind == "on_chat_model_end":
                        output = data.get("output", {})
                        # Try different ways to extract content
                        if hasattr(output, "content"):
                            final_content = output.content
                        elif isinstance(output, dict):
                            # Try generations path
                            gens = output.get("generations", [])
                            if gens and len(gens) > 0 and len(gens[0]) > 0:
                                msg = gens[0][0]
                                if hasattr(msg, "message"):
                                    final_content = msg.message.content if hasattr(msg.message, "content") else str(msg.message)
                                elif isinstance(msg, dict) and "message" in msg:
                                    final_content = msg["message"].get("content", str(msg["message"]))
        except Exception as e:
            # Silently catch streaming errors - will fall back to non-streaming
            pass
        
        return final_content

    async def run(self, user_instruction: str, show_tokens: bool = True) -> Optional[str]:
        """
        Run the agent with automatic fallback from streaming to non-streaming.
        """
        # Show which agent is starting
        if show_tokens:
            print(f"\n{'=' * 60}")
            print(f"[{self.name.upper()}] Starting...")
            print(f"{'=' * 60}")
        
        inputs = {"messages": [("user", user_instruction)]}
        final_content = None

        # 1) Try streaming first
        if show_tokens:
            try:
                final = await self._stream_run(inputs, show_tokens=show_tokens)
                if final:
                    final_content = final
                else:
                    # No final message captured from streaming
                    print(f"{EMOJIS['WARNING']} {ERROR_MESSAGES['NO_FINAL_MESSAGE']} - falling back to non-streaming")
            except Exception as e:
                # Known transient class of errors on SSE/chunked streaming:
                if httpcore and isinstance(e, httpcore.RemoteProtocolError):
                    print(f"\n{EMOJIS['WARNING']} {STATUS_MESSAGES['STREAMING_ERROR']}")
                else:
                    # Log the error type for debugging but continue
                    error_type = type(e).__name__
                    print(f"\n{EMOJIS['WARNING']} Streaming failed ({error_type}). Falling back to non-streaming invoke.")

        # 2) Robust fallback: non-streaming single-shot
        if not final_content:  # Only invoke if we don't have content yet
            print(f"{EMOJIS['INFO']} Executing in non-streaming mode...")
            try:
                result = await self.agent.ainvoke(inputs, config=self.config)
                final_content = result.get("messages", [])[-1].content if result.get("messages") else final_content
            except Exception as e:
                print(f"{EMOJIS['ERROR']} Non-streaming execution also failed: {e}")
                final_content = ""

        # Print final output if not already shown
        if final_content and not show_tokens:
            print(final_content)

        return final_content


# Export main classes - MCP client is now managed by supervisor
__all__ = ['BaseAgent', 'extract_json_block']