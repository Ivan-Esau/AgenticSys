#!/usr/bin/env python3
"""
GitLab MCP Server Tool Inspector

This script connects to the GitLab MCP server and lists all available tools
with their descriptions, parameters, and usage information.
"""

import asyncio
import json
from typing import Dict, Any, List
from langchain_mcp_adapters.client import MultiServerMCPClient
from src.core.llm.config import Config


async def inspect_mcp_tools():
    """
    Connect to GitLab MCP server and inspect all available tools.
    """
    print("=" * 80)
    print("GITLAB MCP SERVER - TOOL INSPECTION")
    print("=" * 80)
    
    # Get MCP configuration
    mcp_url = Config.get_mcp_url()
    print(f"MCP Server URL: {mcp_url}")
    print(f"Transport: {Config.MCP_TRANSPORT}")
    print()
    
    try:
        # Initialize MCP client
        print("[INFO] Connecting to GitLab MCP server...")
        client = MultiServerMCPClient({
            "gitlab": {
                "url": mcp_url,
                "transport": Config.MCP_TRANSPORT
            }
        })
        
        # Get all tools
        print("[INFO] Fetching available tools...")
        tools = await client.get_tools(server_name="gitlab")
        
        print(f"[SUCCESS] Found {len(tools)} tools\n")
        
        # Organize tools by category
        categorized_tools = categorize_tools(tools)
        
        # Display tools by category
        for category, tool_list in categorized_tools.items():
            print(f"\n{'=' * 60}")
            print(f"[CATEGORY] {category.upper()} TOOLS ({len(tool_list)} tools)")
            print(f"{'=' * 60}")
            
            for tool in tool_list:
                display_tool_info(tool)
        
        # Display summary
        print("\n" + "=" * 80)
        print("[SUMMARY] TOOL SUMMARY")
        print("=" * 80)
        
        for category, tool_list in categorized_tools.items():
            print(f"* {category}: {len(tool_list)} tools")
        
        print(f"\n[TOTAL] Total Tools Available: {len(tools)}")
        
        # Close client
        # Close client if method exists
        if hasattr(client, 'close'):
            await client.close()
        elif hasattr(client, 'aclose'):
            await client.aclose()
        
    except Exception as e:
        print(f"❌ Error inspecting MCP tools: {e}")
        import traceback
        traceback.print_exc()


def categorize_tools(tools: List[Any]) -> Dict[str, List[Any]]:
    """
    Categorize tools by their functionality.
    """
    categories = {
        "Repository Management": [],
        "File Operations": [],
        "Issue Management": [],
        "Merge Requests": [],
        "Branch Operations": [],
        "Project Information": [],
        "Pipeline/CI": [],
        "User/Group Management": [],
        "Other": []
    }
    
    for tool in tools:
        tool_name = getattr(tool, 'name', 'unknown')
        
        # Categorize based on tool name patterns
        if any(keyword in tool_name.lower() for keyword in ['repository', 'repo', 'clone', 'fork']):
            categories["Repository Management"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['file', 'content', 'upload', 'download', 'push']):
            categories["File Operations"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['issue', 'issues']):
            categories["Issue Management"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['merge', 'mr', 'pull']):
            categories["Merge Requests"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['branch', 'tag', 'commit']):
            categories["Branch Operations"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['project', 'get_project', 'list_project']):
            categories["Project Information"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['pipeline', 'ci', 'job', 'runner']):
            categories["Pipeline/CI"].append(tool)
        elif any(keyword in tool_name.lower() for keyword in ['user', 'group', 'member']):
            categories["User/Group Management"].append(tool)
        else:
            categories["Other"].append(tool)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def display_tool_info(tool: Any):
    """
    Display detailed information about a single tool.
    """
    tool_name = getattr(tool, 'name', 'Unknown')
    description = getattr(tool, 'description', 'No description available')
    
    print(f"\n[TOOL] {tool_name}")
    print(f"   Description: {description}")
    
    # Try to get input schema if available
    if hasattr(tool, 'input_schema'):
        schema = tool.input_schema
        if isinstance(schema, dict):
            display_tool_schema(schema)
    elif hasattr(tool, 'args_schema'):
        # Alternative schema location
        try:
            schema = tool.args_schema
            if schema:
                display_pydantic_schema(schema)
        except:
            pass
    
    print()


def display_tool_schema(schema: Dict[str, Any]):
    """
    Display tool input schema information.
    """
    if 'properties' in schema:
        print("   Parameters:")
        for param_name, param_info in schema['properties'].items():
            param_type = param_info.get('type', 'unknown')
            param_desc = param_info.get('description', 'No description')
            required = param_name in schema.get('required', [])
            required_marker = " *" if required else ""
            
            print(f"     - {param_name} ({param_type}){required_marker}: {param_desc}")


def display_pydantic_schema(schema_class):
    """
    Display Pydantic model schema information.
    """
    try:
        if hasattr(schema_class, 'model_fields'):
            print("   Parameters:")
            for field_name, field_info in schema_class.model_fields.items():
                field_type = getattr(field_info, 'annotation', 'unknown')
                # Try to get description from field_info
                field_desc = getattr(field_info, 'description', 'No description')
                required = not getattr(field_info, 'default', None)
                required_marker = " *" if required else ""
                
                print(f"     - {field_name} ({field_type}){required_marker}: {field_desc}")
    except Exception as e:
        print(f"     (Could not parse schema: {e})")


async def test_tool_connection():
    """
    Test basic connection to MCP server.
    """
    print("[INFO] Testing MCP server connection...")
    try:
        client = MultiServerMCPClient({
            "gitlab": {
                "url": Config.get_mcp_url(),
                "transport": Config.MCP_TRANSPORT
            }
        })
        
        # Try to get server info
        tools = await client.get_tools(server_name="gitlab")
        print(f"[SUCCESS] Connection successful! Found {len(tools)} tools.")
        
        # Close client if method exists
        if hasattr(client, 'close'):
            await client.close()
        elif hasattr(client, 'aclose'):
            await client.aclose()
        return True
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False


def save_tools_to_json(tools: List[Any], filename: str = "mcp_tools.json"):
    """
    Save tool information to JSON file for further analysis.
    """
    try:
        tools_data = []
        for tool in tools:
            tool_info = {
                "name": getattr(tool, 'name', 'unknown'),
                "description": getattr(tool, 'description', ''),
            }
            
            # Try to extract schema information
            if hasattr(tool, 'input_schema'):
                tool_info['schema'] = tool.input_schema
            
            tools_data.append(tool_info)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tools_data, f, indent=2, ensure_ascii=False)
        
        print(f"[SAVED] Tool information saved to {filename}")
        
    except Exception as e:
        print(f"[ERROR] Failed to save tools to JSON: {e}")


async def main():
    """
    Main execution function.
    """
    print("GitLab MCP Server Tool Inspector")
    print("This script will analyze all available tools from the GitLab MCP server.")
    print()
    
    # Test connection first
    if not await test_tool_connection():
        print("[ERROR] Cannot connect to MCP server. Please check your configuration.")
        return
    
    print()
    
    # Inspect all tools
    await inspect_mcp_tools()
    
    # Optionally save to JSON
    try:
        client = MultiServerMCPClient({
            "gitlab": {
                "url": Config.get_mcp_url(),
                "transport": Config.MCP_TRANSPORT
            }
        })
        tools = await client.get_tools(server_name="gitlab")
        save_tools_to_json(tools)
        # Close client if method exists
        if hasattr(client, 'close'):
            await client.close()
        elif hasattr(client, 'aclose'):
            await client.aclose()
    except Exception as e:
        print(f"[WARNING] Could not save tools to JSON: {e}")


if __name__ == "__main__":
    asyncio.run(main())