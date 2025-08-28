"""
Configuration module for GitLab Agent System.
Centralizes all environment variables and configuration settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, Any

# Find the project root (where .env file is located)
# Current file is in src/core/llm/, so go up 3 levels to get to project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / '.env'

# Load environment variables from the correct path
load_dotenv(ENV_FILE, override=False)


class Config:
    """Central configuration class for all settings."""
    
    # GitLab Configuration
    GITLAB_URL: str = os.getenv("GITLAB_URL", "https://gitlab.com")
    GITLAB_TOKEN: str = os.getenv("GITLAB_TOKEN", "")
    GITLAB_PROJECT_ID: Optional[str] = os.getenv("GITLAB_PROJECT_ID")
    
    # MCP Server Configuration
    MCP_HOST: str = os.getenv("MCP_HOST", "localhost")
    MCP_PORT: str = os.getenv("MCP_PORT", "3333")
    MCP_PATH: str = os.getenv("MCP_PATH", "/mcp")  # Changed default to /mcp
    MCP_TRANSPORT: str = "streamable_http"
    
    # LLM Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "deepseek")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "5"))
    LLM_STREAM_USAGE: bool = True
    
    # Provider API Keys
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    # Provider Base URLs
    DEEPSEEK_BASE_URL: Optional[str] = os.getenv("DEEPSEEK_BASE_URL")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Runner Configuration
    AUTO_CREATE_RUNNER: bool = os.getenv("AUTO_CREATE_RUNNER", "false").lower() == "true"
    RUNNER_TAGS: list[str] = os.getenv("RUNNER_TAGS", "docker").split(",")
    RUNNER_NAME_PREFIX: str = os.getenv("RUNNER_NAME_PREFIX", "auto-runner")
    
    # Agent Configuration
    DEFAULT_BRANCH: str = os.getenv("DEFAULT_BRANCH", "main")
    MAX_ISSUES_TO_SELECT: int = int(os.getenv("MAX_ISSUES_TO_SELECT", "5"))
    SHOW_TOKENS: bool = os.getenv("SHOW_TOKENS", "true").lower() == "true"
    AGENT_RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "200"))  # LangGraph recursion limit
    
    @classmethod
    def get_mcp_url(cls) -> str:
        """Construct the full MCP server URL."""
        return f"http://{cls.MCP_HOST}:{cls.MCP_PORT}{cls.MCP_PATH}"
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration values."""
        # Always required
        required = {
            "GITLAB_URL": cls.GITLAB_URL,
            "GITLAB_TOKEN": cls.GITLAB_TOKEN,
        }
        
        # Provider-specific API key requirements
        provider = cls.LLM_PROVIDER.lower()
        if provider == "deepseek":
            required["DEEPSEEK_API_KEY"] = cls.DEEPSEEK_API_KEY
        elif provider == "openai":
            required["OPENAI_API_KEY"] = cls.OPENAI_API_KEY
        elif provider == "claude":
            required["ANTHROPIC_API_KEY"] = cls.ANTHROPIC_API_KEY
        elif provider == "groq":
            required["GROQ_API_KEY"] = cls.GROQ_API_KEY
        # Note: Ollama doesn't require API key (local)
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            print(f"WARNING: Missing required configuration: {', '.join(missing)}")
            print("Please check your .env file")
            if provider != "ollama":
                print(f"For {provider.upper()} provider, ensure the corresponding API key is set")
            return False
        
        return True


def env(key: str, default: Any = None) -> Any:
    """Helper function to get environment variables with defaults."""
    return os.getenv(key, default)