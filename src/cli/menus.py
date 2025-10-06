"""
Interactive menu system for the GitLab Agent System.
"""

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from .display import Display


class MenuSystem:
    """Handles all interactive menus for the CLI."""

    def __init__(self):
        self.display = Display()

    def show_main_menu(self) -> Optional[Dict[str, Any]]:
        """Full interactive menu for the entire GitLab Agent System."""
        self.display.print_header("[SYSTEM] GITLAB AGENT SYSTEM - INTERACTIVE MODE")
        print("Welcome! Let's configure your project automation.")
        print()

        # Step 1: Project ID
        project_id = self._get_project_id()
        if not project_id:
            return None

        # Step 2: Operation Mode
        mode, specific_issue, resume_path = self._get_operation_mode()
        if not mode:
            return None

        # Step 3: Tech Stack (only for implementation modes)
        tech_stack = None
        if mode in ["implement", "single"]:
            tech_stack = self._get_tech_stack()

        # Step 4: LLM Provider Selection
        llm_provider = self._get_llm_provider()

        # Step 5: Advanced Options
        debug = self._get_debug_mode()

        # Step 6: Final Confirmation
        config = {
            "project_id": project_id,
            "mode": mode,
            "specific_issue": specific_issue,
            "resume_path": resume_path,
            "tech_stack": tech_stack,
            "llm_provider": llm_provider,
            "debug": debug
        }

        self.display.print_configuration_summary(config)

        if not self.display.prompt_yes_no("\n[START] Start execution with this configuration?"):
            self.display.print_error("Configuration cancelled. Exiting...")
            return None

        return config

    def _get_project_id(self) -> Optional[str]:
        """Get GitLab project ID from user."""
        while True:
            project_id = input("📁 Enter GitLab Project ID: ").strip()
            if project_id:
                self.display.print_success(f"Project ID: {project_id}")
                return project_id
            self.display.print_error("Project ID is required. Please enter a valid project ID.")

    def _get_operation_mode(self) -> Tuple[Optional[str], Optional[str], Optional[Path]]:
        """Get operation mode from user."""
        self.display.print_section("[TARGET] OPERATION MODE")
        self.display.print_option("1", "Analyze Only", "No changes - understand project structure")
        self.display.print_option("2", "Full Implementation", "Implement all open issues")
        self.display.print_option("3", "Single Issue", "Implement one specific issue")
        self.display.print_option("4", "Resume from State", "Continue previous run")

        choice = self.display.prompt_choice("\nSelect mode", 1, 4)
        if not choice:
            return None, None, None

        mode_map = {
            "1": ("analyze", "Analysis Only"),
            "2": ("implement", "Full Implementation"),
            "3": ("single", "Single Issue"),
            "4": ("resume", "Resume from State")
        }
        mode, mode_desc = mode_map[choice]
        self.display.print_success(f"Selected: {mode_desc}")

        specific_issue = None
        resume_path = None

        if mode == "single":
            specific_issue = self._get_specific_issue()
            if not specific_issue:
                return None, None, None

        elif mode == "resume":
            resume_path = self._get_resume_path()
            if not resume_path:
                return None, None, None

        return mode, specific_issue, resume_path

    def _get_specific_issue(self) -> Optional[str]:
        """Get specific issue IID for single issue mode."""
        while True:
            issue_iid = input("\n[TARGET] Enter Issue IID to implement: ").strip()
            if issue_iid:
                self.display.print_success(f"Will implement issue #{issue_iid}")
                return issue_iid
            self.display.print_error("Issue IID is required for single issue mode.")

    def _get_resume_path(self) -> Optional[Path]:
        """Get resume file path."""
        while True:
            resume_file = input("\n📂 Enter path to state file: ").strip()
            if resume_file:
                resume_path = Path(resume_file)
                if resume_path.exists():
                    self.display.print_success(f"Will resume from: {resume_path}")
                    return resume_path
                else:
                    self.display.print_error(f"File not found: {resume_file}")
            else:
                self.display.print_error("State file path is required for resume mode.")

    def _get_tech_stack(self) -> Optional[Dict[str, str]]:
        """Get tech stack configuration."""
        self.display.print_section("[TECH] TECH STACK CONFIGURATION")
        print("  Do you want to specify technologies for new/empty projects?")
        print("  (Existing projects will auto-detect their technology stack)")

        if not self.display.prompt_yes_no("\nConfigure tech stack?", default=False):
            self.display.print_success("Will auto-detect technology stack")
            return None

        return self.show_tech_stack_menu()

    def _get_llm_provider(self) -> Optional[Dict[str, str]]:
        """Get LLM provider configuration."""
        from .llm_menu import LLMMenu
        llm_menu = LLMMenu()
        return llm_menu.show_provider_menu()

    def _get_debug_mode(self) -> bool:
        """Get debug mode preference."""
        self.display.print_section("⚙️ ADVANCED OPTIONS")
        debug = self.display.prompt_yes_no("Enable debug mode?", default=False)
        self.display.print_success(f"Debug mode {'enabled' if debug else 'disabled'}")
        return debug

    def show_tech_stack_menu(self) -> Optional[Dict[str, str]]:
        """Interactive menu for selecting tech stack."""
        self.display.print_header("TECH STACK SELECTION MENU", width=60)
        print("Choose technologies for your new project:")
        print("(Leave empty to auto-detect for existing projects)")
        print()

        tech_stack = {}

        # Backend selection
        backend = self._select_backend()
        if backend:
            tech_stack["backend"] = backend

        # Frontend selection
        frontend = self._select_frontend()
        if frontend:
            tech_stack["frontend"] = frontend

        # Database selection
        database = self._select_database()
        if database:
            tech_stack["database"] = database

        if tech_stack:
            print(f"\n[OK] TECH STACK CONFIGURED:")
            for key, value in tech_stack.items():
                print(f"   {key.title()}: {value}")

            if not self.display.prompt_yes_no("\nProceed with this configuration?"):
                self.display.print_error("Configuration cancelled.")
                return None

        return tech_stack if tech_stack else None

    def _select_backend(self) -> Optional[str]:
        """Select backend language."""
        backend_options = [
            ("1", "Python", "python"),
            ("2", "JavaScript/Node.js", "javascript"),
            ("3", "Java", "java"),
            ("4", "C#/.NET", "csharp"),
            ("5", "Go", "go"),
            ("6", "Other/Skip", None)
        ]

        self.display.print_section("[TECH] BACKEND LANGUAGE")
        for option, desc, _ in backend_options:
            self.display.print_option(option, desc)

        choice = self.display.prompt_choice("\nSelect backend", 1, 6, allow_empty=True)
        if not choice:
            return None

        for option, desc, value in backend_options:
            if choice == option:
                if value:
                    self.display.print_success(f"Selected: {desc}")
                else:
                    self.display.print_success("Will auto-detect or skip backend")
                return value

        return None

    def _select_frontend(self) -> Optional[str]:
        """Select frontend framework."""
        frontend_options = [
            ("1", "Basic Web (HTML/CSS/JavaScript)", "html-css-js"),
            ("2", "Modern Web App (React/Vue/Angular)", "web"),
            ("3", "Desktop App (Windows/Mac/Linux)", "desktop"),
            ("4", "Mobile App (iOS/Android)", "mobile"),
            ("5", "API Only (No UI)", "api-only"),
            ("6", "Other/Skip", None)
        ]

        self.display.print_section("🎨 FRONTEND FRAMEWORK")
        for option, desc, _ in frontend_options:
            self.display.print_option(option, desc)

        choice = self.display.prompt_choice("\nSelect frontend", 1, 6, allow_empty=True)
        if not choice:
            return None

        for option, desc, value in frontend_options:
            if choice == option:
                if value:
                    self.display.print_success(f"Selected: {desc}")
                else:
                    self.display.print_success("Will auto-detect or skip frontend")
                return value

        return None

    def _select_database(self) -> Optional[str]:
        """Select database system."""
        database_options = [
            ("1", "Relational Database (PostgreSQL/MySQL)", "relational"),
            ("2", "Document Database (MongoDB)", "mongodb"),
            ("3", "Simple/Embedded (SQLite)", "sqlite"),
            ("4", "Other/Skip", None)
        ]

        self.display.print_section("🗄️ DATABASE SYSTEM")
        for option, desc, _ in database_options:
            self.display.print_option(option, desc)

        choice = self.display.prompt_choice("\nSelect database", 1, 4, allow_empty=True)
        if not choice:
            return None

        for option, desc, value in database_options:
            if choice == option:
                if value:
                    self.display.print_success(f"Selected: {desc}")
                else:
                    self.display.print_success("Will auto-detect or skip database")
                return value

        return None