"""
Utility functions for handling pipeline configuration consistently.
Provides a single interface for accessing config across all prompts.
"""

from typing import Dict, Any, Optional


def extract_tech_stack(pipeline_config: Any) -> Dict[str, str]:
    """
    Extract tech stack information from pipeline config.
    Handles both new (attribute) and old (dictionary) formats.
    Also handles Web GUI format with 'language', 'framework', 'testing' fields.

    Args:
        pipeline_config: Pipeline configuration object or dict

    Returns:
        Dictionary with backend, frontend, database keys
    """
    tech_stack = {
        "backend": "python",
        "frontend": "Not specified",
        "database": "Not specified",
        "testing": "Not specified"
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
        if hasattr(pipeline_config, 'testing'):
            tech_stack["testing"] = pipeline_config.testing

    # Handle dictionary formats
    elif isinstance(pipeline_config, dict):
        # Web GUI format: {'language': 'Java', 'framework': 'Spring', 'testing': 'JUnit', ...}
        if 'language' in pipeline_config:
            tech_stack["backend"] = pipeline_config.get('language', 'python')
            tech_stack["frontend"] = pipeline_config.get('framework', 'Not specified')
            tech_stack["database"] = pipeline_config.get('database', 'Not specified')
            tech_stack["testing"] = pipeline_config.get('testing', 'Not specified')
        # Old tech_stack nested format
        elif 'tech_stack' in pipeline_config:
            old_stack = pipeline_config['tech_stack']
            # Check for Web GUI format inside tech_stack
            if 'language' in old_stack:
                tech_stack["backend"] = old_stack.get('language', 'python')
                tech_stack["frontend"] = old_stack.get('framework', 'Not specified')
                tech_stack["database"] = old_stack.get('database', 'Not specified')
                tech_stack["testing"] = old_stack.get('testing', 'Not specified')
            else:
                # Standard format
                tech_stack["backend"] = old_stack.get('backend', 'python')
                tech_stack["frontend"] = old_stack.get('frontend', 'Not specified')
                tech_stack["database"] = old_stack.get('database', 'Not specified')
                tech_stack["testing"] = old_stack.get('testing', 'Not specified')
        # Direct config dict format (backend/frontend keys)
        elif 'backend' in pipeline_config:
            tech_stack["backend"] = pipeline_config.get('backend', 'python')
            tech_stack["frontend"] = pipeline_config.get('frontend', 'Not specified')
            tech_stack["database"] = pipeline_config.get('database', 'Not specified')
            tech_stack["testing"] = pipeline_config.get('testing', 'Not specified')

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
    backend = tech_stack["backend"].upper()
    testing = tech_stack["testing"]

    messages = {
        "planning": f"""
CONFIGURED TECH STACK (USER-SELECTED - USE THIS EXACTLY):
- Language/Backend: {backend}
- Testing Framework: {testing}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

⚠️ CRITICAL: The user explicitly selected {backend} and {testing}.
⚠️ You MUST create a {backend} project structure, NOT Python or any other language.
⚠️ Example for {backend}:
   - Java → pom.xml, src/main/java/, src/test/java/ with JUnit tests
   - Python → requirements.txt, src/, tests/ with pytest
   - JavaScript → package.json, src/, __tests__/ with Jest
⚠️ DO NOT auto-detect tech stack from existing files - use the configured values above.
""",
        "coding": f"""
CONFIGURED TECH STACK (USER-SELECTED - USE THIS EXACTLY):
- Language/Backend: {backend}
- Testing Framework: {testing}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

⚠️ CRITICAL: Implement ALL code in {backend}, NOT Python or any other language.
⚠️ Use {testing} for testing.
⚠️ Do not create Python files if the language is Java, or vice versa.
""",
        "testing": f"""
CONFIGURED TECH STACK (USER-SELECTED):
- Language/Backend: {backend}
- Testing Framework: {testing}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

⚠️ IMPORTANT: Write tests using {testing} for {backend} code.
""",
        "review": f"""
CONFIGURED TECH STACK (USER-SELECTED):
- Language/Backend: {backend}
- Testing Framework: {testing}
- Frontend: {tech_stack["frontend"]}
- Database: {tech_stack["database"]}

⚠️ IMPORTANT: This project uses {backend} with {testing} as specified by the user.
""",
        "generic": f"""
CONFIGURED TECH STACK:
- Language/Backend: {backend}
- Testing Framework: {testing}
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