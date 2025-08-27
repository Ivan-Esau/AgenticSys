"""
MCP (Model Context Protocol) client module.
Handles connection and tool loading from GitLab MCP server.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient
from ..core.config import Config
from typing import Tuple, List, Any


async def load_mcp_tools() -> Tuple[List[Any], MultiServerMCPClient]:
    """
    Initialize MCP client and load GitLab tools.
    
    Returns:
        Tuple of (tools list, MCP client instance)
    """
    url = Config.get_mcp_url()
    
    # Suppress MCP initialization errors/warnings
    import logging
    import sys
    import os
    from contextlib import redirect_stdout, redirect_stderr
    
    # Temporarily disable MCP-related logging during initialization
    mcp_loggers = [
        logging.getLogger('langchain_mcp_adapters'),
        logging.getLogger('mcp'),
        logging.getLogger('httpx'),
        logging.getLogger('httpcore')
    ]
    
    original_levels = {}
    for logger in mcp_loggers:
        original_levels[logger] = logger.level
        logger.setLevel(logging.ERROR)  # Only show actual errors, not warnings
    
    try:
        # Initialize multi-server MCP client with comprehensive suppression
        with open(os.devnull, 'w') as devnull:
            with redirect_stderr(devnull), redirect_stdout(devnull):  # Suppress all output during init
                client = MultiServerMCPClient({
                    "gitlab": {
                        "url": url,
                        "transport": Config.MCP_TRANSPORT
                    }
                })
                
                # Load tools from GitLab server
                tools = await client.get_tools(server_name="gitlab")
        
        return tools, client
    
    finally:
        # Restore original logging levels
        for logger, level in original_levels.items():
            logger.setLevel(level)


async def get_common_tools_and_client() -> Tuple[List[Any], MultiServerMCPClient]:
    """
    Get common tools and MCP client for agents.
    This is the primary entry point for agents needing GitLab tools.
    
    Returns:
        Tuple of (tools list, MCP client instance)
    """
    # Validate configuration before connecting
    if not Config.validate():
        raise ValueError("Invalid configuration. Please check your .env file.")
    
    tools, client = await load_mcp_tools()
    
    return tools, client


class SafeMCPClient:
    """Wrapper around MCP client that safely handles close operations"""
    
    def __init__(self, client: MultiServerMCPClient):
        self._client = client
        self._closed = False
    
    async def close(self):
        """Safely close the MCP client, suppressing session termination errors"""
        if self._closed:
            return
        
        try:
            # Try to close if the client has a close method
            if hasattr(self._client, 'close'):
                # Use a more sophisticated approach to suppress errors
                import logging
                import sys
                import os
                from contextlib import redirect_stdout, redirect_stderr, suppress
                
                # Temporarily disable logging for MCP-related loggers
                mcp_loggers = [
                    logging.getLogger('langchain_mcp_adapters'),
                    logging.getLogger('mcp'),
                    logging.getLogger('httpx'),
                    logging.getLogger('httpcore')
                ]
                
                original_levels = {}
                for logger in mcp_loggers:
                    original_levels[logger] = logger.level
                    logger.setLevel(logging.CRITICAL)
                
                try:
                    # Redirect stdout/stderr to suppress console output
                    with open(os.devnull, 'w') as devnull:
                        with redirect_stdout(devnull), redirect_stderr(devnull):
                            with suppress(Exception):  # Suppress all exceptions during close
                                await self._client.close()
                finally:
                    # Restore original logging levels
                    for logger, level in original_levels.items():
                        logger.setLevel(level)
                        
        except Exception:
            # Silently ignore any close errors - they're not critical
            pass
        finally:
            self._closed = True
            print("[SUPERVISOR] MCP client closed cleanly")
    
    def __getattr__(self, name):
        """Proxy all other attributes to the wrapped client"""
        return getattr(self._client, name)