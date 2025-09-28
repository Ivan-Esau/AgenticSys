"""
Configuration management for the CLI.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path


class CLIConfig:
    """Manages CLI configuration and environment settings."""

    def __init__(self):
        self.config = {}

    def setup_environment(self):
        """Setup environment for cross-platform compatibility."""
        import sys

        # Set UTF-8 encoding for Windows
        if sys.platform == 'win32':
            os.system('chcp 65001 > nul 2>&1')
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    def apply_llm_configuration(self, llm_provider: Optional[Dict[str, str]]):
        """Apply LLM provider configuration to environment."""
        if not llm_provider:
            return

        # Set provider
        os.environ["LLM_PROVIDER"] = llm_provider["provider"]

        # Set model if specified
        if llm_provider.get("model"):
            provider = llm_provider["provider"]
            model = llm_provider["model"]

            # Map provider to environment variable
            provider_env_map = {
                "deepseek": "DEEPSEEK_MODEL",
                "openai": "OPENAI_MODEL",
                "claude": "CLAUDE_MODEL",
                "groq": "GROQ_MODEL",
                "ollama": "OLLAMA_MODEL"
            }

            if provider in provider_env_map:
                os.environ[provider_env_map[provider]] = model

    def apply_cli_configuration(self, config: Dict[str, Any]):
        """Apply CLI configuration from arguments."""
        if not config:
            return

        # Apply LLM provider settings
        if "llm_provider" in config:
            if isinstance(config["llm_provider"], str):
                os.environ["LLM_PROVIDER"] = config["llm_provider"]
            elif isinstance(config["llm_provider"], dict):
                self.apply_llm_configuration(config["llm_provider"])

        # Store configuration
        self.config = config

    def get_mode_description(self, mode: str, specific_issue: Optional[str] = None) -> str:
        """Get human-readable description for operation mode."""
        mode_descriptions = {
            'analyze': 'Analysis Only (No Changes)',
            'implement': 'Full Implementation (All Issues)',
            'single': f"Single Issue Implementation (Issue #{specific_issue or 'N/A'})",
            'resume': 'Resume from State'
        }
        return mode_descriptions.get(mode, f"Unknown mode: {mode}")

    def validate_configuration(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate configuration dictionary."""
        # Required fields
        if not config.get("project_id"):
            return False, "Project ID is required"

        if not config.get("mode"):
            return False, "Operation mode is required"

        # Mode-specific validation
        mode = config["mode"]
        if mode == "single" and not config.get("specific_issue"):
            return False, "Issue ID is required for single issue mode"

        if mode == "resume":
            resume_path = config.get("resume_path")
            if not resume_path:
                return False, "Resume file path is required for resume mode"
            if isinstance(resume_path, str):
                resume_path = Path(resume_path)
            if not resume_path.exists():
                return False, f"Resume file not found: {resume_path}"

        return True, None

    def build_supervisor_params(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for supervisor orchestrator."""
        params = {
            "project_id": config["project_id"],
            "mode": config["mode"],
            "specific_issue": config.get("specific_issue"),
            "resume_from": config.get("resume_path"),
            "tech_stack": config.get("tech_stack")
        }

        # Remove None values
        return {k: v for k, v in params.items() if v is not None}

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "mode": "analyze",
            "debug": False,
            "tech_stack": None,
            "llm_provider": None
        }