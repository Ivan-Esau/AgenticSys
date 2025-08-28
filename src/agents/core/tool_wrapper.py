"""
Tool wrapping and caching functionality.
Wraps tools with caching capabilities and integrates with state management.
"""

from typing import List, Any, Optional, Dict, Callable
from pydantic import BaseModel, Field
from src.core.context.state import ProjectState
from .cache_manager import CacheManager


class ToolWrapper:
    """
    Wraps tools with caching capabilities and state integration.
    Provides intelligent caching for file operations.
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    def wrap_tools_with_cache(self, tools: List[Any]) -> List[Any]:
        """
        Wrap tools with caching capability, particularly for file operations.
        
        Args:
            tools: List of original tools to wrap
            
        Returns:
            List of wrapped tools with caching
        """
        wrapped_tools = []
        
        for tool in tools:
            # Check if this is a get_file_contents tool that needs caching
            if hasattr(tool, 'name') and tool.name == 'get_file_contents':
                wrapped_tool = self._create_cached_file_tool(tool)
                wrapped_tools.append(wrapped_tool)
            else:
                wrapped_tools.append(tool)
        
        return wrapped_tools
    
    def _create_cached_file_tool(self, original_tool: Any) -> Any:
        """
        Create a cached version of the file reading tool.
        
        Args:
            original_tool: Original file reading tool
            
        Returns:
            Cached version of the tool
        """
        from langchain_core.tools import tool
        
        class FileInput(BaseModel):
            file: str = Field(description="File path to read")
        
        @tool("get_file_contents", args_schema=FileInput, return_direct=False)
        def cached_get_file_contents(file: str) -> str:
            """Get file contents with intelligent caching."""
            tool_input = {"file": file}
            
            # Check cache first
            cached_result = self.cache_manager.check_file_cache("get_file_contents", tool_input)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - call original tool
            try:
                if hasattr(original_tool, 'invoke'):
                    result = original_tool.invoke(tool_input)
                elif callable(original_tool):
                    result = original_tool(file)
                else:
                    # Fallback to async call if needed
                    import asyncio
                    async def async_call():
                        if hasattr(original_tool, 'ainvoke'):
                            return await original_tool.ainvoke(tool_input)
                        else:
                            return str(original_tool)
                    
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Create new event loop if current one is running
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(asyncio.run, async_call())
                                result = future.result()
                        else:
                            result = loop.run_until_complete(async_call())
                    except:
                        result = str(original_tool)
                
                # Cache the result
                result_str = str(result)
                self.cache_manager.cache_file_result("get_file_contents", tool_input, result_str)
                return result_str
                
            except Exception as e:
                error_msg = f"Error reading file {file}: {e}"
                print(f"  [ERROR] {error_msg}")
                return error_msg
        
        return cached_get_file_contents
    
    def create_langchain_cached_tool(self, original_tool: Any) -> Any:
        """
        Create a LangChain-compatible cached tool with async support.
        
        Args:
            original_tool: Original tool to wrap
            
        Returns:
            Async cached tool
        """
        from langchain_core.tools import tool
        
        class FileInput(BaseModel):
            file: str = Field(description="File path to read")
        
        def sync_cached_get_file_contents(file: str) -> str:
            """Synchronous cached file reader."""
            tool_input = {"file": file}
            
            # Check cache first
            cached_result = self.cache_manager.check_file_cache("get_file_contents", tool_input)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - need to call async version
            import asyncio
            
            async def async_call():
                try:
                    if hasattr(original_tool, 'ainvoke'):
                        result = await original_tool.ainvoke(tool_input)
                    elif hasattr(original_tool, 'invoke'):
                        result = original_tool.invoke(tool_input)
                    else:
                        result = str(original_tool)
                    return str(result)
                except Exception as e:
                    return f"Error reading file {file}: {e}"
            
            # Handle async call from sync context
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Need to run in thread if loop is already running
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, async_call())
                        result = future.result()
                else:
                    result = loop.run_until_complete(async_call())
            except Exception as e:
                result = f"Error in async execution: {e}"
            
            # Cache the result
            self.cache_manager.cache_file_result("get_file_contents", tool_input, result)
            return result
        
        # Create the tool with proper async support
        @tool("get_file_contents", args_schema=FileInput, return_direct=False)
        async def async_cached_get_file_contents(file: str) -> str:
            """Async cached file reader."""
            tool_input = {"file": file}
            
            # Check cache first
            cached_result = self.cache_manager.check_file_cache("get_file_contents", tool_input)
            if cached_result is not None:
                return cached_result
            
            # Cache miss - call original tool
            try:
                if hasattr(original_tool, 'ainvoke'):
                    result = await original_tool.ainvoke(tool_input)
                elif hasattr(original_tool, 'invoke'):
                    result = original_tool.invoke(tool_input)
                elif callable(original_tool):
                    result = original_tool(file)
                else:
                    result = str(original_tool)
                
                result_str = str(result)
                self.cache_manager.cache_file_result("get_file_contents", tool_input, result_str)
                return result_str
                
            except Exception as e:
                error_msg = f"Error reading file {file}: {e}"
                print(f"  [ERROR] {error_msg}")
                return error_msg
        
        return async_cached_get_file_contents