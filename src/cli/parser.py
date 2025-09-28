"""
Command-line argument parser for the GitLab Agent System.
"""

import argparse
from typing import Optional, List
from pathlib import Path


class ArgumentParser:
    """Handles command-line argument parsing."""

    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            description="GitLab Agent System - Automated Project Implementation",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
INTERACTIVE MODE (Recommended):
  # Full interactive experience - no arguments needed:
  python run.py

CLI MODE (Advanced users):
  # Analyze project:
  python run.py --project-id 113

  # Implement with tech stack:
  python run.py --project-id 114 --apply --backend-lang python --frontend-lang react

  # Interactive tech stack menu:
  python run.py --project-id 114 --apply --menu
            """
        )

        # Core arguments
        parser.add_argument(
            "--project-id",
            type=str,
            help="GitLab project ID"
        )

        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes (implement code). Without this, only analysis is done."
        )

        parser.add_argument(
            "--issue",
            type=str,
            help="Specific issue ID to implement (single issue mode)"
        )

        parser.add_argument(
            "--resume",
            type=str,
            help="Path to state file to resume from"
        )

        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output and full stack traces"
        )

        # Tech stack arguments
        parser.add_argument(
            "--backend-lang",
            type=str,
            choices=["python", "javascript", "typescript", "java", "csharp", "go", "rust", "php"],
            help="Backend language for new projects (auto-detected for existing projects)"
        )

        parser.add_argument(
            "--frontend-lang",
            type=str,
            choices=["javascript", "typescript", "react", "vue", "angular", "svelte", "html"],
            help="Frontend language/framework for new projects (auto-detected for existing projects)"
        )

        parser.add_argument(
            "--database",
            type=str,
            choices=["postgresql", "mysql", "sqlite", "mongodb", "redis", "cassandra", "influxdb", "neo4j"],
            help="Database system for new projects"
        )

        parser.add_argument(
            "--menu",
            action="store_true",
            help="Show interactive tech stack selection menu"
        )

        # LLM provider arguments
        parser.add_argument(
            "--llm-provider",
            type=str,
            help="LLM provider (deepseek, openai, claude, groq, ollama)"
        )

        parser.add_argument(
            "--llm-model",
            type=str,
            help="Specific model name for the chosen provider"
        )

        return parser

    @staticmethod
    def parse_to_config(args: argparse.Namespace) -> dict:
        """Convert parsed arguments to configuration dictionary."""
        config = {}

        # Required field
        config["project_id"] = args.project_id

        # Determine mode
        if args.issue:
            config["mode"] = "single"
            config["specific_issue"] = args.issue
        elif args.apply:
            config["mode"] = "implement"
        else:
            config["mode"] = "analyze"

        # Resume mode
        if args.resume:
            config["mode"] = "resume"
            config["resume_path"] = Path(args.resume)

        # Debug mode
        config["debug"] = args.debug

        # Tech stack
        tech_stack = {}
        if args.backend_lang:
            tech_stack["backend"] = args.backend_lang
        if args.frontend_lang:
            tech_stack["frontend"] = args.frontend_lang
        if args.database:
            tech_stack["database"] = args.database

        if tech_stack:
            config["tech_stack"] = tech_stack
        else:
            config["tech_stack"] = None

        # Menu flag
        config["show_menu"] = args.menu

        # LLM configuration
        if args.llm_provider:
            config["llm_provider"] = {
                "provider": args.llm_provider,
                "model": args.llm_model
            }

        return config

    @staticmethod
    def get_dynamic_provider_choices() -> List[str]:
        """Get available LLM providers dynamically from configuration."""
        try:
            from src.core.llm.model_config_loader import get_model_config_loader
            loader = get_model_config_loader()
            return loader.get_available_providers()
        except:
            # Fallback to default list if loading fails
            return ["deepseek", "openai", "claude", "groq", "ollama"]

    @staticmethod
    def validate_args(args: argparse.Namespace) -> tuple[bool, Optional[str]]:
        """Validate parsed arguments."""
        # Check if project ID is provided in CLI mode
        if args.project_id is None:
            return True, None  # Will use interactive mode

        # Validate resume file if specified
        if args.resume:
            resume_path = Path(args.resume)
            if not resume_path.exists():
                return False, f"Resume file not found: {args.resume}"

        # Validate that model is only specified with provider
        if args.llm_model and not args.llm_provider:
            return False, "LLM model can only be specified with a provider (--llm-provider)"

        return True, None