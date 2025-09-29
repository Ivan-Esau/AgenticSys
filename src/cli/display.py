"""
Display utilities for CLI output formatting.
"""

from typing import Optional, Dict, Any


class Display:
    """Handles all display formatting for the CLI."""

    BANNER = """
================================================================================
                         GITLAB AGENT SYSTEM
                    Automated Project Implementation
================================================================================

    Architecture: Supervisor Pattern with Shared State
    Agents: Planning, Coding, Testing, Review, Pipeline

================================================================================
    """

    @staticmethod
    def print_banner():
        """Print welcome banner."""
        print(Display.BANNER)

    @staticmethod
    def print_header(title: str, width: int = 70):
        """Print a formatted header."""
        print("\n" + "=" * width)
        print(title.center(width))
        print("=" * width)

    @staticmethod
    def print_section(title: str, icon: str = ""):
        """Print a section header."""
        icon_str = f"{icon} " if icon else ""
        print(f"\n{icon_str}{title}:")

    @staticmethod
    def print_option(number: str, text: str, description: str = ""):
        """Print a menu option."""
        print(f"  {number}. {text}")
        if description:
            print(f"      {description}")

    @staticmethod
    def print_status(message: str, success: bool = True):
        """Print a status message."""
        icon = "✓" if success else "❌"
        print(f"{icon} {message}")

    @staticmethod
    def print_error(message: str):
        """Print an error message."""
        print(f"❌ {message}")

    @staticmethod
    def print_success(message: str):
        """Print a success message."""
        print(f"✓ {message}")

    @staticmethod
    def print_warning(message: str):
        """Print a warning message."""
        print(f"⚠️  {message}")

    @staticmethod
    def print_info(message: str):
        """Print an info message."""
        print(f"ℹ️  {message}")

    @staticmethod
    def print_configuration_summary(config: Dict[str, Any]):
        """Print configuration summary."""
        Display.print_header("[CONFIG] CONFIGURATION SUMMARY")

        print(f"Project ID: {config.get('project_id', 'Not set')}")

        # Mode description
        mode = config.get('mode', 'unknown')
        mode_descriptions = {
            'analyze': 'Analysis Only (No Changes)',
            'implement': 'Full Implementation (All Issues)',
            'single': f"Single Issue Implementation (Issue #{config.get('specific_issue', 'N/A')})",
            'resume': 'Resume from State'
        }
        print(f"Operation Mode: {mode_descriptions.get(mode, mode)}")

        # Optional fields
        if config.get('specific_issue'):
            print(f"Target Issue: #{config['specific_issue']}")

        if config.get('resume_path'):
            print(f"Resume From: {config['resume_path']}")

        # Tech stack
        tech_stack = config.get('tech_stack')
        if tech_stack:
            print("Tech Stack:")
            for key, value in tech_stack.items():
                print(f"  {key.title()}: {value}")
        else:
            print("Tech Stack: Auto-detect")

        # LLM provider
        llm_provider = config.get('llm_provider')
        if llm_provider:
            if isinstance(llm_provider, dict):
                print(f"LLM Provider: {llm_provider.get('provider', 'Default').upper()}")
                if llm_provider.get('model'):
                    print(f"  Model: {llm_provider['model']}")
            else:
                print(f"LLM Provider: {llm_provider}")
        else:
            print("LLM Provider: Default (from .env)")

        # Debug mode
        debug = config.get('debug', False)
        print(f"Debug Mode: {'Enabled' if debug else 'Disabled'}")

        print("=" * 70)

    @staticmethod
    def prompt_user(message: str, default: Optional[str] = None) -> str:
        """Prompt user for input with optional default."""
        prompt = message
        if default:
            prompt += f" (default: {default})"
        prompt += ": "

        response = input(prompt).strip()
        if not response and default:
            return default
        return response

    @staticmethod
    def prompt_yes_no(message: str, default: bool = True) -> bool:
        """Prompt user for yes/no confirmation."""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{message} ({default_str}): ").strip().lower()
            if response in ["", "y", "yes"]:
                return True if (response or default) else False
            elif response in ["n", "no"]:
                return False
            else:
                Display.print_error("Please enter 'y' for yes or 'n' for no.")

    @staticmethod
    def prompt_choice(message: str, min_val: int, max_val: int, allow_empty: bool = False) -> Optional[str]:
        """Prompt user for a numeric choice."""
        while True:
            if allow_empty:
                choice = input(f"{message} ({min_val}-{max_val}, or Enter to skip): ").strip()
                if not choice:
                    return None
            else:
                choice = input(f"{message} ({min_val}-{max_val}): ").strip()

            if choice.isdigit() and min_val <= int(choice) <= max_val:
                return choice
            else:
                Display.print_error(f"Please select {min_val}-{max_val}{' or press Enter to skip' if allow_empty else ''}.")