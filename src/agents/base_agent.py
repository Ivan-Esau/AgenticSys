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
        """Wrap tools with caching functionality using LangChain-compatible approach"""
        if not self.state:
            return tools
        
        wrapped_tools = []
        for tool in tools:
            if hasattr(tool, 'name') and tool.name == 'get_file_contents':
                # Create a proper LangChain tool wrapper that respects async/sync patterns
                cached_tool = self._create_langchain_cached_tool(tool)
                wrapped_tools.append(cached_tool)
                print(f"[CACHING] Wrapped get_file_contents tool with LangChain-compatible caching")
            else:
                wrapped_tools.append(tool)
        
        return wrapped_tools
    
    def _create_langchain_cached_tool(self, original_tool):
        """Create a LangChain-compatible cached tool using StructuredTool.from_function"""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field
        import asyncio
        
        # Define input schema for the wrapper - keeps simple interface
        class FileInput(BaseModel):
            file: str = Field(description="File path to read")
        
        # Create sync cached function
        def sync_cached_get_file_contents(file: str) -> str:
            """Get file contents with intelligent caching (sync version)"""
            # Check cache first
            if self.state:
                cached_result = self.state.get_cached_file(file)
                if cached_result:
                    print(f"  [CACHE HIT] File: {file}")
                    return cached_result
            
            # Not in cache - MCP tools are async-only, so we need to run async in sync context
            try:
                import asyncio
                
                async def async_call():
                    # Convert to MCP tool format with correct parameters
                    project_id = self.project_id if hasattr(self, 'project_id') else "114"
                    return await original_tool.ainvoke({
                        "project_id": project_id,
                        "file_path": file
                    })
                
                # Handle different async contexts
                try:
                    # Try to get existing event loop
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # We're in an async context - return cache miss message
                        print(f"  [CACHE MISS] File: {file} (async context - returning error)")
                        return f"[SYNC ERROR] File {file} - MCP tools require async context"
                    else:
                        result = loop.run_until_complete(async_call())
                except RuntimeError:
                    # No event loop - create one
                    result = asyncio.run(async_call())
                
                # Extract content from MCP response if it's JSON
                if result and isinstance(result, str):
                    try:
                        import json
                        parsed = json.loads(result)
                        if isinstance(parsed, dict) and 'content' in parsed:
                            result = parsed['content']
                    except (json.JSONDecodeError, KeyError):
                        # Not JSON or no content field, use as-is
                        pass
                
                # Cache the result
                if self.state and isinstance(result, str) and result:
                    self.state.cache_file(file, result)
                    print(f"  [CACHED] File: {file} ({len(result)} chars)")
                
                return result
            except Exception as e:
                print(f"  [CACHE ERROR] Sync tool call failed: {e}")
                return f"Error reading file: {e}"
        
        # Create async cached function
        async def async_cached_get_file_contents(file: str) -> str:
            """Get file contents with intelligent caching (async version)"""
            # Check cache first
            if self.state:
                cached_result = self.state.get_cached_file(file)
                if cached_result:
                    print(f"  [CACHE HIT] File: {file}")
                    return cached_result
            
            # Not in cache - call original tool with correct parameters
            try:
                project_id = self.project_id if hasattr(self, 'project_id') else "114"
                result = await original_tool.ainvoke({
                    "project_id": project_id,
                    "file_path": file
                })
                
                # Extract content from MCP response if it's JSON
                if result and isinstance(result, str):
                    try:
                        import json
                        parsed = json.loads(result)
                        if isinstance(parsed, dict) and 'content' in parsed:
                            result = parsed['content']
                    except (json.JSONDecodeError, KeyError):
                        # Not JSON or no content field, use as-is
                        pass
                
                # Cache the result
                if self.state and isinstance(result, str) and result:
                    self.state.cache_file(file, result)
                    print(f"  [CACHED] File: {file} ({len(result)} chars)")
                
                return result
            except Exception as e:
                print(f"  [CACHE ERROR] Async tool call failed: {e}")
                return f"Error reading file: {e}"
        
        # Create proper StructuredTool with both sync and async support
        try:
            return StructuredTool.from_function(
                func=sync_cached_get_file_contents,     # Sync version
                coroutine=async_cached_get_file_contents, # Async version
                name="get_file_contents",
                description=getattr(original_tool, 'description', 'Get file contents with caching'),
                args_schema=FileInput
            )
        except Exception as e:
            print(f"[CACHE WARNING] Could not create cached tool: {e}")
            return original_tool  # Fallback to original
    
    def _create_cached_file_tool(self, original_tool):
        """Create a cached version of the get_file_contents tool"""
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field
        
        # Define the input schema (matching original tool)
        class FileInput(BaseModel):
            file: str = Field(description="File path to read")
            
        def cached_get_file_contents(file: str) -> str:
            """Get file contents with caching support"""
            # Check cache first
            if self.state:
                cached_result = self.state.get_cached_file(file)
                if cached_result:
                    print(f"  [CACHE HIT] File: {file}")
                    return cached_result
            
            # Not in cache - call original tool
            # LangChain tools are complex - just call the original and handle async internally
            try:
                import asyncio
                
                # Create async wrapper
                async def async_call():
                    try:
                        return await original_tool.ainvoke({"file": file})
                    except:
                        # Fallback to sync if available
                        try:
                            return original_tool.invoke({"file": file})
                        except:
                            return original_tool.run({"file": file})
                
                # Run in event loop
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're already in an async context, we need to handle this differently
                        # For now, just indicate cache miss and return original tool behavior
                        print(f"  [CACHE MISS] File: {file} (async context)")
                        return f"[CACHE MISS] {file} - would call original tool"
                    else:
                        result = loop.run_until_complete(async_call())
                except:
                    # If no event loop, create one
                    result = asyncio.run(async_call())
                
                # Cache the result
                if self.state and isinstance(result, str) and result:
                    self.state.cache_file(file, result)
                    print(f"  [CACHED] File: {file} ({len(result)} chars)")
                
                return result
            except Exception as e:
                print(f"  [ERROR] Failed to read file {file}: {e}")
                return f"Error reading file: {e}"
        
        # Create new tool with caching function
        return StructuredTool.from_function(
            func=cached_get_file_contents,
            name="get_file_contents",
            description="Get file contents with caching support",
            args_schema=FileInput
        )
    
    

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
        # Handle LangGraph version compatibility for prompt parameter
        try:
            self.agent = create_react_agent(
                model=self.model,
                tools=self.tools,
                messages_modifier=self.system_prompt
            )
        except TypeError:
            # Fallback for older LangGraph versions
            try:
                self.agent = create_react_agent(
                    model=self.model,
                    tools=self.tools,
                    state_modifier=self.system_prompt
                )
            except TypeError:
                # Final fallback to prompt parameter
                self.agent = create_react_agent(
                    model=self.model,
                    tools=self.tools,
                    prompt=self.system_prompt
                )
        
        # Store config with higher recursion limit from configuration
        self.config = {"recursion_limit": Config.AGENT_RECURSION_LIMIT}  # Default: 200

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