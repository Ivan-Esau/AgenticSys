"""
MCP Integration Module
Handles MCP server interactions and tool management.
"""

import json
from typing import Dict, List, Optional, Any


class MCPIntegration:
    """
    Manages MCP server integration and tool interactions.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.tools = []
        self.client = None
        self.default_branch = "master"

    async def initialize(self, mcp_tools, client):
        """Initialize MCP integration with tools and client."""
        self.tools = mcp_tools
        self.client = client

        print(f"\n[MCP] Initialized for project {self.project_id}")
        print(f"[MCP] {len(mcp_tools)} tools available")

        # Fetch project info to get actual default branch
        await self.fetch_project_info()

    async def fetch_project_info(self):
        """Fetch project information and update state."""
        try:
            get_project_tool = self.get_tool('get_project')

            if get_project_tool:
                # Get project info
                project_info = await get_project_tool.ainvoke({"project_id": self.project_id})

                if isinstance(project_info, dict):
                    # Update default branch if available
                    if 'default_branch' in project_info:
                        self.default_branch = project_info['default_branch']
                        print(f"[PROJECT] Default branch: {self.default_branch}")
                    else:
                        print(f"[PROJECT] Using default branch: {self.default_branch}")
                elif isinstance(project_info, str):
                    # Try to parse as JSON
                    try:
                        parsed_info = json.loads(project_info)
                        if 'default_branch' in parsed_info:
                            self.default_branch = parsed_info['default_branch']
                            print(f"[PROJECT] Default branch: {self.default_branch}")
                    except json.JSONDecodeError:
                        print(f"[PROJECT] Could not parse project info as JSON")
            else:
                print(f"[PROJECT] get_project tool not found, using default branch: {self.default_branch}")

        except Exception as e:
            print(f"[PROJECT] Failed to fetch project info: {e}")
            print(f"[PROJECT] Using default branch: {self.default_branch}")

    def get_tool(self, tool_name: str):
        """Get a tool by name."""
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                return tool
        return None

    def get_tools(self) -> List[Any]:
        """Get all available tools."""
        return self.tools

    def get_default_branch(self) -> str:
        """Get the default branch name."""
        return self.default_branch

    async def cleanup(self):
        """Clean up MCP client resources."""
        if self.client:
            await self.client.close()