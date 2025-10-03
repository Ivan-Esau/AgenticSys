"""
MCP (Model Context Protocol) client module.
Handles connection and tool loading from GitLab MCP server.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient
from src.core.llm.config import Config
from typing import Tuple, List, Any, Optional

# Global cache for MCP connection
_mcp_cache: Optional[Tuple[List[Any], MultiServerMCPClient]] = None

async def load_mcp_tools(log_callback=None) -> Tuple[List[Any], MultiServerMCPClient]:
    """
    Initialize MCP client and load GitLab tools.
    Uses caching to avoid recreating connections.

    Args:
        log_callback: Optional async function to send logs (for WebSocket integration)

    Returns:
        Tuple of (tools list, MCP client instance)
    """
    global _mcp_cache

    async def log(message: str, level: str = "info"):
        """Helper to log both to console and WebSocket"""
        print(message)
        if log_callback:
            try:
                await log_callback(message, level)
            except:
                pass  # Don't fail if WebSocket logging fails

    # Return cached connection if available
    if _mcp_cache is not None:
        tools, client = _mcp_cache
        await log(f"[MCP] Using cached connection ({len(tools)} tools)", "info")
        return tools, client

    url = Config.get_mcp_url()
    await log(f"[MCP] Connecting to {url}...", "info")

    # Suppress MCP initialization errors/warnings
    import logging
    import os
    import sys
    from contextlib import redirect_stdout, redirect_stderr

    # Temporarily disable MCP-related logging during initialization
    mcp_loggers = [
        logging.getLogger('langchain_mcp_adapters'),
        logging.getLogger('mcp'),
        logging.getLogger('httpx'),
        logging.getLogger('httpcore'),
        logging.getLogger('asyncio')
    ]

    original_levels = {}
    for logger in mcp_loggers:
        original_levels[logger] = logger.level
        logger.setLevel(logging.CRITICAL)  # Only show critical errors

    # Suppress stderr session termination messages during init
    original_stderr = sys.stderr

    try:
        # Initialize multi-server MCP client with timeout
        import asyncio

        async def init_client():
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

        try:
            # Add timeout to prevent hanging
            tools, client = await asyncio.wait_for(init_client(), timeout=10.0)
            await log(f"[MCP] Successfully connected! Loaded {len(tools)} tools", "success")

            # Cache the connection for reuse
            _mcp_cache = (tools, client)

            # Return tools directly - wrapping breaks LangGraph compatibility
            return tools, client

        except asyncio.TimeoutError:
            await log(f"[MCP] ERROR: Connection timeout after 10 seconds!", "error")
            await log(f"[MCP] Please check if MCP server is running at {url}", "error")
            raise RuntimeError(f"MCP connection timeout - server may be down or unresponsive")
        except Exception as e:
            # Show connection errors to help debug
            await log(f"[MCP] Warning: Error during MCP initialization: {str(e)[:100]}", "warning")
            raise

    finally:
        # Restore original logging levels and stderr
        sys.stderr = original_stderr
        for logger, level in original_levels.items():
            logger.setLevel(level)



def clear_mcp_cache():
    """Clear the MCP connection cache to force reconnection."""
    global _mcp_cache
    _mcp_cache = None
    print("[MCP] Cache cleared - next call will create new connection")


async def get_common_tools_and_client(log_callback=None) -> Tuple[List[Any], MultiServerMCPClient]:
    """
    Get common tools and MCP client for agents.
    This is the primary entry point for agents needing GitLab tools.

    Args:
        log_callback: Optional async function to send logs (for WebSocket integration)

    Returns:
        Tuple of (tools list, MCP client instance)
    """
    # Validate configuration before connecting
    if not Config.validate():
        raise ValueError("Invalid configuration. Please check your .env file.")

    tools, client = await load_mcp_tools(log_callback)

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