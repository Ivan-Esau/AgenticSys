"""
Tech Stack Detection Module
Detects project technology stack without hardcoded MCP tool dependencies.
"""

from typing import Dict, Any, List
import json


class TechStackDetector:
    """
    Detects project technology stack from user input or configuration files.
    Does NOT directly call MCP tools - agents handle that themselves.
    """

    @staticmethod
    def from_user_input(tech_stack: Dict[str, str]) -> Dict[str, str]:
        """
        Process user-provided tech stack configuration.

        Args:
            tech_stack: User input like {'language': 'Java', 'framework': None}

        Returns:
            Normalized format: {'backend': 'java', 'frontend': 'none'}
        """
        normalized = {}

        # Map 'language' to 'backend' and convert to lowercase
        if 'language' in tech_stack:
            language = tech_stack['language']
            if language:
                normalized['backend'] = language.lower()

        # Map framework/frontend
        if 'framework' in tech_stack:
            framework = tech_stack.get('framework')
            if framework and framework.lower() != 'none':
                normalized['frontend'] = framework.lower()
            else:
                normalized['frontend'] = 'none'
        else:
            normalized['frontend'] = 'none'

        # Copy other config values
        for key in ['min_coverage', 'test_framework', 'build_tool']:
            if key in tech_stack:
                normalized[key] = tech_stack[key]

        return normalized

    @staticmethod
    def from_file_patterns(file_list: list[str]) -> Dict[str, str]:
        """
        Detect tech stack from list of file names.
        This is a simple heuristic-based approach.

        Args:
            file_list: List of file names like ['pom.xml', 'package.json', 'README.md']

        Returns:
            Detected tech stack: {'backend': 'java', 'frontend': 'none'}
        """
        tech_stack = {'backend': 'unknown', 'frontend': 'none'}

        # Backend detection
        if 'pom.xml' in file_list:
            tech_stack['backend'] = 'java'
        elif 'build.gradle' in file_list or 'build.gradle.kts' in file_list:
            tech_stack['backend'] = 'java'
        elif 'package.json' in file_list:
            tech_stack['backend'] = 'nodejs'
        elif 'requirements.txt' in file_list or 'setup.py' in file_list or 'pyproject.toml' in file_list:
            tech_stack['backend'] = 'python'
        elif 'Cargo.toml' in file_list:
            tech_stack['backend'] = 'rust'
        elif 'go.mod' in file_list:
            tech_stack['backend'] = 'go'

        # Frontend detection
        if 'package.json' in file_list:
            # Could be React, Vue, Angular - need deeper analysis
            # For now, keep as 'none' unless we find specific framework files
            pass

        return tech_stack

    @staticmethod
    def get_default() -> Dict[str, str]:
        """Get default fallback tech stack."""
        return {
            'backend': 'python',
            'frontend': 'none'
        }

    @staticmethod
    def validate_tech_stack(tech_stack: Dict[str, str]) -> bool:
        """
        Validate tech stack configuration.

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(tech_stack, dict):
            return False

        if 'backend' not in tech_stack:
            return False

        valid_backends = ['java', 'python', 'nodejs', 'rust', 'go', 'unknown', 'auto-detect']
        if tech_stack['backend'] not in valid_backends:
            return False

        return True

    @staticmethod
    async def detect_from_repository(project_id: str, mcp_tools: List[Any]) -> Dict[str, str]:
        """
        Detect tech stack by examining repository files using MCP tools.
        Uses dynamic tool discovery - no hardcoded tool names.

        Args:
            project_id: GitLab project ID
            mcp_tools: List of available MCP tools

        Returns:
            Detected tech stack dict like {'backend': 'java', 'frontend': 'none'}
        """
        try:
            # Find a tool that can list repository contents
            # Look for tools with names containing 'tree', 'list', or 'repository'
            repo_tool = None
            for tool in mcp_tools:
                if hasattr(tool, 'name'):
                    tool_name = tool.name.lower()
                    if any(keyword in tool_name for keyword in ['tree', 'repository', 'files', 'contents']):
                        if 'list' in tool_name or 'get' in tool_name or 'tree' in tool_name:
                            repo_tool = tool
                            print(f"[TECH STACK] Using tool '{tool.name}' for detection")
                            break

            if not repo_tool:
                print("[TECH STACK] No repository listing tool found, using default")
                return TechStackDetector.get_default()

            # Call the tool to get repository file tree
            # Try different parameter variations
            result = None
            try:
                # Try with project_id parameter
                result = await repo_tool.ainvoke({'project_id': project_id})
            except Exception as e:
                print(f"[TECH STACK] First attempt failed: {e}")
                try:
                    # Try with id parameter
                    result = await repo_tool.ainvoke({'id': project_id})
                except Exception as e2:
                    print(f"[TECH STACK] Second attempt failed: {e2}")
                    return TechStackDetector.get_default()

            # Parse the result to get list of files
            file_list = []
            if isinstance(result, str):
                try:
                    parsed = json.loads(result)
                    if isinstance(parsed, list):
                        # Extract file names/paths from tree structure
                        for item in parsed:
                            if isinstance(item, dict):
                                # Look for 'name', 'path', or 'file' keys
                                name = item.get('name') or item.get('path') or item.get('file')
                                if name:
                                    file_list.append(name)
                            elif isinstance(item, str):
                                file_list.append(item)
                except json.JSONDecodeError:
                    # Not JSON, treat as plain text file list
                    file_list = [line.strip() for line in result.split('\n') if line.strip()]

            elif isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        name = item.get('name') or item.get('path') or item.get('file')
                        if name:
                            file_list.append(name)
                    elif isinstance(item, str):
                        file_list.append(item)

            if not file_list:
                print("[TECH STACK] No files found in repository, using default")
                return TechStackDetector.get_default()

            # Use file pattern detection
            detected = TechStackDetector.from_file_patterns(file_list)
            print(f"[TECH STACK] Auto-detected from {len(file_list)} files: {detected.get('backend', 'unknown')}")
            return detected

        except Exception as e:
            print(f"[TECH STACK] Detection failed: {e}")
            import traceback
            traceback.print_exc()
            return TechStackDetector.get_default()
