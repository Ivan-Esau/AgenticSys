"""
Utility functions for handling pipeline configuration consistently.
Provides a single interface for accessing config across all prompts.
"""

from typing import Dict, Any, Optional


def extract_tech_stack(pipeline_config: Any) -> Dict[str, str]:
    """
    Extract tech stack information from pipeline config.
    Handles both new (attribute) and old (dictionary) formats.

    Args:
        pipeline_config: Pipeline configuration object or dict

    Returns:
        Dictionary with backend, frontend, database keys
    """
    tech_stack = {
        "backend": "python",
        "frontend": "Not specified",
        "database": "Not specified"
    }

    if not pipeline_config:
        return tech_stack

    # Handle new format (direct attributes from supervisor)
    if hasattr(pipeline_config, 'backend'):
        tech_stack["backend"] = pipeline_config.backend
        if hasattr(pipeline_config, 'frontend'):
            tech_stack["frontend"] = pipeline_config.frontend
        if hasattr(pipeline_config, 'database'):
            tech_stack["database"] = pipeline_config.database

    # Handle old format (dictionary from pipeline)
    elif isinstance(pipeline_config, dict):
        if 'tech_stack' in pipeline_config:
            old_stack = pipeline_config['tech_stack']
            tech_stack["backend"] = old_stack.get('backend', 'python')
            tech_stack["frontend"] = old_stack.get('frontend', 'Not specified')
            tech_stack["database"] = old_stack.get('database', 'Not specified')
        # Direct config dict format
        elif 'backend' in pipeline_config:
            tech_stack["backend"] = pipeline_config.get('backend', 'python')
            tech_stack["frontend"] = pipeline_config.get('frontend', 'Not specified')
            tech_stack["database"] = pipeline_config.get('database', 'Not specified')

    return tech_stack


def get_tech_stack_prompt(pipeline_config: Any, agent_type: str = "generic") -> str:
    """
    Generate tech stack prompt section for any agent.

    Args:
        pipeline_config: Pipeline configuration
        agent_type: Type of agent for context-specific messaging

    Returns:
        Formatted tech stack prompt section
    """
    tech_stack = extract_tech_stack(pipeline_config)

    if tech_stack["backend"] == "python" and tech_stack["frontend"] == "Not specified":
        # Likely using defaults, no explicit user choice
        return ""

    backend = tech_stack["backend"].upper()

    messages = {
        "planning": f"""
CONFIGURED TECH STACK (USE THIS - DO NOT DETECT FROM EXISTING FILES):
- Backend: {backend}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

IMPORTANT: The user has explicitly chosen {backend} as the backend.
Even if existing files suggest Python or another language, you MUST plan for {backend}.
""",
        "coding": f"""
CONFIGURED TECH STACK (USE THIS - DO NOT DETECT FROM EXISTING FILES):
- Backend: {backend}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

IMPORTANT: The user has explicitly chosen {backend} as the backend.
You MUST implement code in {backend}, even if existing files suggest Python or another language.
""",
        "testing": f"""
CONFIGURED TECH STACK (USE THIS - DO NOT DETECT FROM EXISTING FILES):
- Backend: {backend}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

IMPORTANT: Write tests for {backend} code, matching the user's chosen stack.
""",
        "review": f"""
CONFIGURED TECH STACK (USER-SPECIFIED):
- Backend: {backend}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

IMPORTANT: This project uses {backend} as specified by the user.
""",
        "generic": f"""
CONFIGURED TECH STACK:
- Backend: {backend}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}
"""
    }

    return messages.get(agent_type, messages["generic"])


def get_config_value(pipeline_config: Any, key: str, default: Any = None) -> Any:
    """
    Safely get a configuration value from pipeline config.

    Args:
        pipeline_config: Pipeline configuration
        key: Configuration key to retrieve
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    if not pipeline_config:
        return default

    # Try attribute access first
    if hasattr(pipeline_config, key):
        return getattr(pipeline_config, key)

    # Try dictionary access
    if isinstance(pipeline_config, dict):
        # Check in config sub-dict
        if 'config' in pipeline_config:
            config = pipeline_config['config']
            if key in config:
                return config[key]
        # Check in root dict
        if key in pipeline_config:
            return pipeline_config[key]

    return default