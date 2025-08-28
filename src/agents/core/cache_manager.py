"""
File caching management for agents.
Handles caching and retrieval of file contents.
"""

from typing import Optional, Dict, Any
from src.core.context.state import ProjectState


class CacheManager:
    """
    Manages file caching for agent operations.
    Provides cache hit/miss logic and result caching.
    """
    
    def __init__(self, state: ProjectState):
        self.state = state
    
    def check_file_cache(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """
        Check cache for file operations and return cached content if available.
        
        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters for the tool
            
        Returns:
            Cached content if available, None otherwise
        """
        if not self.state:
            return None
        
        if tool_name == 'get_file_contents':
            file_path = tool_input.get('file', '')
            cached_content = self.state.get_cached_file(file_path)
            if cached_content:
                print(f"  [CACHE HIT] File: {file_path} (from state cache)")
                return cached_content
        
        return None
    
    def cache_file_result(self, tool_name: str, tool_input: Dict[str, Any], result: str) -> None:
        """
        Cache the result of a file operation for future use.
        
        Args:
            tool_name: Name of the tool that was called
            tool_input: Input parameters used
            result: Result to cache
        """
        if not self.state:
            return
        
        if tool_name == 'get_file_contents':
            file_path = tool_input.get('file', '')
            if file_path and result:
                self.state.cache_file(file_path, result)
                print(f"  [CACHED] File: {file_path}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.state or not hasattr(self.state, 'file_cache'):
            return {"cached_files": 0}
        
        return {
            "cached_files": len(self.state.file_cache),
            "cache_hits": getattr(self.state, 'cache_hits', 0),
            "cache_misses": getattr(self.state, 'cache_misses', 0)
        }