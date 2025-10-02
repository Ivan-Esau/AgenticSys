"""
Main CLI runner that coordinates all CLI components.
"""

import sys
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from .display import Display
from .config import CLIConfig
from .parser import ArgumentParser
from .menus import MenuSystem


class CLIRunner:
    """Main runner for the CLI application."""

    def __init__(self):
        self.display = Display()
        self.config_manager = CLIConfig()
        self.menu_system = MenuSystem()
        self.parser = ArgumentParser.create_parser()

    async def run(self) -> int:
        """Main entry point for the CLI."""
        try:
            # Setup environment
            self.config_manager.setup_environment()

            # Parse arguments
            args = self.parser.parse_args()

            # Validate arguments
            is_valid, error = ArgumentParser.validate_args(args)
            if not is_valid:
                self.display.print_error(f"Invalid arguments: {error}")
                return 1

            # Get configuration (either from args or interactive menu)
            config = await self._get_configuration(args)
            if not config:
                return 1  # User cancelled or error

            # Validate configuration
            is_valid, error = self.config_manager.validate_configuration(config)
            if not is_valid:
                self.display.print_error(f"Configuration error: {error}")
                return 1

            # Apply configuration
            self.config_manager.apply_cli_configuration(config)

            # Display banner and configuration
            self.display.print_banner()
            self._display_execution_info(config)

            # Run the supervisor
            return await self._run_supervisor(config)

        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Stopped by user")
            return 130
        except Exception as e:
            print(f"\n[ERROR] Execution failed: {e}")
            if config.get("debug"):
                import traceback
                traceback.print_exc()
            return 1

    async def _get_configuration(self, args) -> Optional[Dict[str, Any]]:
        """Get configuration from arguments or interactive menu."""
        # Check if running in interactive mode (no project ID provided)
        if not args.project_id:
            # Interactive mode
            return self.menu_system.show_main_menu()

        # CLI mode - build config from arguments
        config = ArgumentParser.parse_to_config(args)

        # Tech stack now auto-detected - no menu needed
        # config["tech_stack"] will be None, triggering auto-detection

        # Display configuration summary for CLI mode
        self.display.print_configuration_summary(config)

        return config

    def _display_execution_info(self, config: Dict[str, Any]):
        """Display execution information."""
        mode = config["mode"]
        project_id = config["project_id"]

        mode_desc = self.config_manager.get_mode_description(
            mode,
            config.get("specific_issue")
        )
        print(f"Mode: {mode_desc}")
        print(f"Project ID: {project_id}")

        if config.get("tech_stack"):
            print("Tech Stack Configuration:")
            for key, value in config["tech_stack"].items():
                print(f"  {key.title()}: {value}")

        print()

    async def _run_supervisor(self, config: Dict[str, Any]) -> int:
        """Run the supervisor orchestrator."""
        try:
            # Import supervisor here to avoid circular imports
            from src.orchestrator.supervisor import run_supervisor

            # Build supervisor parameters
            params = self.config_manager.build_supervisor_params(config)

            # Run supervisor
            await run_supervisor(**params)

            print("\n[SUCCESS] Execution completed successfully")
            return 0

        except Exception as e:
            print(f"\n[ERROR] Supervisor execution failed: {e}")
            if config.get("debug"):
                import traceback
                traceback.print_exc()
            return 1


def main():
    """Main entry point for the CLI."""
    runner = CLIRunner()
    exit_code = asyncio.run(runner.run())
    sys.exit(exit_code)