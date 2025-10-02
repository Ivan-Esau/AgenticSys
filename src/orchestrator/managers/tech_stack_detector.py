"""
Tech Stack Detection Module
Detects project technology stack without hardcoded MCP tool dependencies.
"""

from typing import Dict, Any


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

        valid_backends = ['java', 'python', 'nodejs', 'rust', 'go', 'unknown']
        if tech_stack['backend'] not in valid_backends:
            return False

        return True
