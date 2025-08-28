#!/usr/bin/env python3
"""
Main entry point for GitLab Agent System
Single, clean interface to run the entire system
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    os.system('chcp 65001 > nul 2>&1')
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the orchestrator function
from src.orchestrator.supervisor import run_supervisor


def show_main_menu():
    """Full interactive menu for the entire GitLab Agent System"""
    print("\n" + "="*70)
    print("           🚀 GITLAB AGENT SYSTEM - INTERACTIVE MODE")
    print("="*70)
    print("Welcome! Let's configure your project automation.")
    print()
    
    # Step 1: Project ID
    while True:
        project_id = input("📁 Enter GitLab Project ID: ").strip()
        if project_id:
            break
        print("❌ Project ID is required. Please enter a valid project ID.")
    
    print(f"✓ Project ID: {project_id}")
    
    # Step 2: Operation Mode
    print(f"\n🎯 OPERATION MODE:")
    print("  1. Analyze Only (No changes - understand project structure)")
    print("  2. Full Implementation (Implement all open issues)")
    print("  3. Single Issue (Implement one specific issue)")
    print("  4. Resume from State (Continue previous run)")
    
    while True:
        mode_choice = input("\nSelect mode (1-4): ").strip()
        if mode_choice in ["1", "2", "3", "4"]:
            break
        print("❌ Please select 1, 2, 3, or 4.")
    
    mode_map = {
        "1": ("analyze", "Analysis Only"),
        "2": ("implement", "Full Implementation"),
        "3": ("single", "Single Issue"),
        "4": ("resume", "Resume from State")
    }
    mode, mode_desc = mode_map[mode_choice]
    print(f"✓ Selected: {mode_desc}")
    
    # Step 3: Additional options based on mode
    specific_issue = None
    resume_path = None
    
    if mode == "single":
        while True:
            specific_issue = input("\n🎯 Enter Issue ID to implement: ").strip()
            if specific_issue:
                break
            print("❌ Issue ID is required for single issue mode.")
        print(f"✓ Will implement issue #{specific_issue}")
        
    elif mode == "resume":
        while True:
            resume_file = input("\n📂 Enter path to state file: ").strip()
            if resume_file:
                from pathlib import Path
                resume_path = Path(resume_file)
                if resume_path.exists():
                    break
                else:
                    print(f"❌ File not found: {resume_file}")
            else:
                print("❌ State file path is required for resume mode.")
        print(f"✓ Will resume from: {resume_path}")
    
    # Step 4: Tech Stack (only for implementation modes)
    tech_stack = None
    if mode in ["implement", "single"]:
        print(f"\n🔧 TECH STACK CONFIGURATION:")
        print("  Do you want to specify technologies for new/empty projects?")
        print("  (Existing projects will auto-detect their technology stack)")
        
        while True:
            tech_choice = input("\nConfigure tech stack? (y/N): ").strip().lower()
            if tech_choice in ["", "n", "no"]:
                tech_stack = None
                print("✓ Will auto-detect technology stack")
                break
            elif tech_choice in ["y", "yes"]:
                tech_stack = show_tech_stack_menu()
                if tech_stack is None:
                    print("❌ Tech stack configuration cancelled. Using auto-detect.")
                break
            else:
                print("❌ Please enter 'y' for yes or 'n' for no (default).")
    
    # Step 4.5: LLM Provider Selection
    llm_provider = None
    provider_config = show_llm_provider_menu()
    if provider_config:
        llm_provider = provider_config
        print(f"✓ Selected LLM provider: {provider_config['provider'].upper()}")
    
    # Step 5: Advanced Options
    print(f"\n⚙️ ADVANCED OPTIONS:")
    
    debug = False
    debug_choice = input("Enable debug mode? (y/N): ").strip().lower()
    if debug_choice in ["y", "yes"]:
        debug = True
        print("✓ Debug mode enabled")
    else:
        print("✓ Debug mode disabled")
    
    # Step 6: Final Confirmation
    print(f"\n" + "="*70)
    print("                    📋 CONFIGURATION SUMMARY")
    print("="*70)
    print(f"Project ID: {project_id}")
    print(f"Operation Mode: {mode_desc}")
    
    if specific_issue:
        print(f"Target Issue: #{specific_issue}")
    if resume_path:
        print(f"Resume From: {resume_path}")
    if tech_stack:
        print("Tech Stack:")
        for key, value in tech_stack.items():
            print(f"  {key.title()}: {value}")
    else:
        print("Tech Stack: Auto-detect")
    
    if llm_provider:
        print(f"LLM Provider: {llm_provider['provider'].upper()}")
        if 'model' in llm_provider and llm_provider['model']:
            print(f"  Model: {llm_provider['model']}")
    else:
        print("LLM Provider: Default (from .env)")
    
    print(f"Debug Mode: {'Enabled' if debug else 'Disabled'}")
    print("="*70)
    
    while True:
        confirm = input("\n🚀 Start execution with this configuration? (Y/n): ").strip().lower()
        if confirm in ["", "y", "yes"]:
            break
        elif confirm in ["n", "no"]:
            print("❌ Configuration cancelled. Exiting...")
            return None
        else:
            print("❌ Please enter 'y' to proceed or 'n' to cancel.")
    
    return {
        "project_id": project_id,
        "mode": mode,
        "specific_issue": specific_issue,
        "resume_path": resume_path,
        "tech_stack": tech_stack,
        "llm_provider": llm_provider,
        "debug": debug
    }


def show_tech_stack_menu():
    """Interactive menu for selecting tech stack"""
    print("\n" + "="*60)
    print("        TECH STACK SELECTION MENU")
    print("="*60)
    print("Choose technologies for your new project:")
    print("(Leave empty to auto-detect for existing projects)")
    print()
    
    # Backend selection - simplified to most popular options
    backend_options = [
        ("1", "Python"),
        ("2", "JavaScript/Node.js"), 
        ("3", "Java"),
        ("4", "C#/.NET"),
        ("5", "Go"),
        ("6", "Other/Skip")
    ]
    
    print("🔧 BACKEND LANGUAGE:")
    for option, desc in backend_options:
        print(f"  {option}. {desc}")
    
    while True:
        backend_choice = input("\nSelect backend (1-6, or Enter to skip): ").strip()
        if backend_choice == "":
            backend = None
            break
        elif backend_choice in [opt[0] for opt in backend_options]:
            backend_map = {
                "1": "python", "2": "javascript", "3": "java", 
                "4": "csharp", "5": "go", "6": None
            }
            backend = backend_map[backend_choice]
            if backend is None:  # Other/Skip option
                backend = None
                print("✓ Will auto-detect or skip backend")
            else:
                selected = next(desc for opt, desc in backend_options if opt == backend_choice)
                print(f"✓ Selected: {selected}")
            break
        else:
            print("❌ Invalid choice. Please select 1-6 or press Enter to skip.")
    
    # Frontend selection - simplified to main categories
    frontend_options = [
        ("1", "Basic Web (HTML/CSS/JavaScript)"),
        ("2", "Modern Web App (React/Vue/Angular)"),
        ("3", "Desktop App (Windows/Mac/Linux)"),
        ("4", "Mobile App (iOS/Android)"),
        ("5", "API Only (No UI)"),
        ("6", "Other/Skip")
    ]
    
    print("\n🎨 FRONTEND FRAMEWORK:")
    for option, desc in frontend_options:
        print(f"  {option}. {desc}")
    
    while True:
        frontend_choice = input("\nSelect frontend (1-6, or Enter to skip): ").strip()
        if frontend_choice == "":
            frontend = None
            break
        elif frontend_choice in [opt[0] for opt in frontend_options]:
            frontend_map = {
                "1": "html-css-js", "2": "web", "3": "desktop", 
                "4": "mobile", "5": "api-only", "6": None
            }
            frontend = frontend_map[frontend_choice]
            if frontend is None:  # Other/Skip option
                frontend = None
                print("✓ Will auto-detect or skip frontend")
            else:
                selected = next(desc for opt, desc in frontend_options if opt == frontend_choice)
                print(f"✓ Selected: {selected}")
            break
        else:
            print("❌ Invalid choice. Please select 1-6 or press Enter to skip.")
    
    # Database selection - simplified to main categories
    database_options = [
        ("1", "Relational Database (PostgreSQL/MySQL)"),
        ("2", "Document Database (MongoDB)"),
        ("3", "Simple/Embedded (SQLite)"),
        ("4", "Other/Skip")
    ]
    
    print("\n🗄️ DATABASE SYSTEM:")
    for option, desc in database_options:
        print(f"  {option}. {desc}")
    
    while True:
        db_choice = input("\nSelect database (1-4, or Enter to skip): ").strip()
        if db_choice == "":
            database = None
            break
        elif db_choice in [opt[0] for opt in database_options]:
            db_map = {
                "1": "relational", "2": "mongodb", "3": "sqlite", "4": None
            }
            database = db_map[db_choice]
            if database is None:  # Other/Skip option
                database = None
                print("✓ Will auto-detect or skip database")
            else:
                selected = next(desc for opt, desc in database_options if opt == db_choice)
                print(f"✓ Selected: {selected}")
            break
        else:
            print("❌ Invalid choice. Please select 1-4 or press Enter to skip.")
    
    # Build tech stack dict
    tech_stack = {}
    if backend:
        tech_stack["backend"] = backend
    if frontend:
        tech_stack["frontend"] = frontend  
    if database:
        tech_stack["database"] = database
        
    if tech_stack:
        print(f"\n✅ TECH STACK CONFIGURED:")
        for key, value in tech_stack.items():
            print(f"   {key.title()}: {value}")
        
        confirm = input("\nProceed with this configuration? (Y/n): ").strip().lower()
        if confirm in ['n', 'no']:
            print("❌ Configuration cancelled.")
            return None
            
    return tech_stack if tech_stack else None


def show_java_framework_menu():
    """Java framework selection submenu"""
    print(f"\n  ☕ JAVA FRAMEWORK:")
    print("  1. Spring Boot (Most popular, batteries included)")
    print("  2. Spring Framework (Traditional Spring)")
    print("  3. Quarkus (Cloud-native, fast startup)")
    print("  4. Micronaut (Lightweight, microservices)")
    print("  5. Jakarta EE (Enterprise, app servers)")
    print("  6. Spark Java (Lightweight web framework)")
    
    while True:
        choice = input("  Select Java framework (1-6): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6"]:
            framework_map = {
                "1": "java-spring-boot",
                "2": "java-spring",
                "3": "java-quarkus", 
                "4": "java-micronaut",
                "5": "java-jakarta-ee",
                "6": "java-spark"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "Spring Boot", "2": "Spring Framework", "3": "Quarkus",
                "4": "Micronaut", "5": "Jakarta EE", "6": "Spark Java"
            }
            print(f"  ✓ Java Framework: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-6.")


def show_python_framework_menu():
    """Python framework selection submenu"""
    print(f"\n  🐍 PYTHON FRAMEWORK:")
    print("  1. FastAPI (Modern, async, auto docs)")
    print("  2. Django (Full-featured, batteries included)")
    print("  3. Flask (Lightweight, flexible)")
    print("  4. Django REST Framework (API-focused)")
    print("  5. Starlette (Async web toolkit)")
    
    while True:
        choice = input("  Select Python framework (1-5): ").strip()
        if choice in ["1", "2", "3", "4", "5"]:
            framework_map = {
                "1": "python-fastapi",
                "2": "python-django",
                "3": "python-flask",
                "4": "python-drf",
                "5": "python-starlette"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "FastAPI", "2": "Django", "3": "Flask", 
                "4": "Django REST Framework", "5": "Starlette"
            }
            print(f"  ✓ Python Framework: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-5.")


def show_javascript_framework_menu():
    """JavaScript framework selection submenu"""
    print(f"\n  🟨 JAVASCRIPT FRAMEWORK:")
    print("  1. Express.js (Most popular, minimal)")
    print("  2. Nest.js (Enterprise, TypeScript-like)")
    print("  3. Koa.js (Next-gen Express)")
    print("  4. Fastify (High performance)")
    print("  5. Hapi.js (Enterprise, configuration)")
    
    while True:
        choice = input("  Select JavaScript framework (1-5): ").strip()
        if choice in ["1", "2", "3", "4", "5"]:
            framework_map = {
                "1": "javascript-express",
                "2": "javascript-nestjs",
                "3": "javascript-koa",
                "4": "javascript-fastify",
                "5": "javascript-hapi"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "Express.js", "2": "Nest.js", "3": "Koa.js",
                "4": "Fastify", "5": "Hapi.js"
            }
            print(f"  ✓ JavaScript Framework: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-5.")


def show_csharp_framework_menu():
    """C# framework selection submenu"""
    print(f"\n  🟦 C# FRAMEWORK:")
    print("  1. ASP.NET Core (Cross-platform, modern)")
    print("  2. ASP.NET Framework (Windows, traditional)")
    print("  3. Minimal APIs (.NET 6+, lightweight)")
    print("  4. Blazor Server (Server-side rendering)")
    print("  5. Web API (API-focused)")
    
    while True:
        choice = input("  Select C# framework (1-5): ").strip()
        if choice in ["1", "2", "3", "4", "5"]:
            framework_map = {
                "1": "csharp-aspnet-core",
                "2": "csharp-aspnet-framework",
                "3": "csharp-minimal-api",
                "4": "csharp-blazor",
                "5": "csharp-webapi"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "ASP.NET Core", "2": "ASP.NET Framework", "3": "Minimal APIs",
                "4": "Blazor Server", "5": "Web API"
            }
            print(f"  ✓ C# Framework: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-5.")


def show_native_desktop_menu():
    """Native desktop UI framework selection"""
    print(f"\n  🖥️ NATIVE DESKTOP UI:")
    print("  1. Qt (C++/Python/C# - Cross-platform)")
    print("  2. GTK (C/Python - Linux/Windows/macOS)")
    print("  3. Tkinter (Python - Built-in)")
    print("  4. WPF (C# - Windows)")
    print("  5. WinForms (C# - Windows)")
    print("  6. Swing (Java - Cross-platform)")
    print("  7. JavaFX (Java - Modern)")
    print("  8. Cocoa (Swift/Objective-C - macOS)")
    print("  9. Win32 API (C++ - Windows)")
    print("  10. FLTK (C++ - Lightweight)")
    
    while True:
        choice = input("  Select desktop UI framework (1-10): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
            framework_map = {
                "1": "native-qt", "2": "native-gtk", "3": "native-tkinter",
                "4": "native-wpf", "5": "native-winforms", "6": "native-swing",
                "7": "native-javafx", "8": "native-cocoa", "9": "native-win32",
                "10": "native-fltk"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "Qt", "2": "GTK", "3": "Tkinter", "4": "WPF", "5": "WinForms",
                "6": "Swing", "7": "JavaFX", "8": "Cocoa", "9": "Win32 API", "10": "FLTK"
            }
            print(f"  ✓ Desktop UI: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-10.")


def show_mobile_menu():
    """Mobile development framework selection"""
    print(f"\n  📱 MOBILE DEVELOPMENT:")
    print("  1. Native iOS (Swift/Objective-C)")
    print("  2. Native Android (Kotlin/Java)")
    print("  3. React Native (JavaScript/TypeScript)")
    print("  4. Flutter (Dart - Google)")
    print("  5. Xamarin (C# - Microsoft)")
    print("  6. Ionic (Web technologies)")
    print("  7. Cordova/PhoneGap (Web wrapper)")
    print("  8. NativeScript (JavaScript/TypeScript)")
    
    while True:
        choice = input("  Select mobile framework (1-8): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            framework_map = {
                "1": "mobile-ios-native", "2": "mobile-android-native",
                "3": "mobile-react-native", "4": "mobile-flutter",
                "5": "mobile-xamarin", "6": "mobile-ionic",
                "7": "mobile-cordova", "8": "mobile-nativescript"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "Native iOS", "2": "Native Android", "3": "React Native",
                "4": "Flutter", "5": "Xamarin", "6": "Ionic", "7": "Cordova", "8": "NativeScript"
            }
            print(f"  ✓ Mobile Framework: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-8.")


def show_cross_platform_menu():
    """Cross-platform development framework selection"""
    print(f"\n  🌐 CROSS-PLATFORM DEVELOPMENT:")
    print("  1. Electron (Web tech for desktop)")
    print("  2. Tauri (Rust + Web for desktop)")
    print("  3. Flutter (Desktop + Mobile)")
    print("  4. Qt (Desktop + Mobile + Embedded)")
    print("  5. .NET MAUI (Microsoft cross-platform)")
    print("  6. Unity (Game engine - all platforms)")
    print("  7. Avalonia (C# - cross-platform UI)")
    print("  8. Wails (Go + Web for desktop)")
    
    while True:
        choice = input("  Select cross-platform framework (1-8): ").strip()
        if choice in ["1", "2", "3", "4", "5", "6", "7", "8"]:
            framework_map = {
                "1": "cross-electron", "2": "cross-tauri", "3": "cross-flutter",
                "4": "cross-qt", "5": "cross-maui", "6": "cross-unity",
                "7": "cross-avalonia", "8": "cross-wails"
            }
            framework = framework_map[choice]
            framework_names = {
                "1": "Electron", "2": "Tauri", "3": "Flutter", "4": "Qt",
                "5": ".NET MAUI", "6": "Unity", "7": "Avalonia", "8": "Wails"
            }
            print(f"  ✓ Cross-Platform: {framework_names[choice]}")
            return framework
        else:
            print("  ❌ Please select 1-8.")


def show_llm_provider_menu():
    """Interactive menu for selecting LLM provider"""
    from src.core.llm.llm_providers import validate_provider_config
    from src.core.llm.model_config_loader import get_model_config_loader
    
    print(f"\n🤖 LLM PROVIDER CONFIGURATION:")
    print("  Select your preferred Large Language Model provider:")
    print("  (Default provider from .env will be used if skipped)")
    print()
    
    # Load provider information from JSON configs
    loader = get_model_config_loader()
    available_providers = loader.get_available_providers()
    provider_summary = loader.get_provider_summary()
    
    print("🤖 AVAILABLE PROVIDERS:")
    provider_options = []
    
    option_num = 1
    for provider in available_providers:
        if provider in provider_summary:
            summary = provider_summary[provider]
            display_name = summary["display_name"]
            description = summary["description"]
            is_valid = summary["valid"]
            
            status_icon = "✅" if is_valid else "⚠️"
            provider_options.append((str(option_num), provider, display_name, description))
            print(f"  {option_num}. {display_name} - {description} {status_icon}")
            option_num += 1
    
    skip_option = str(option_num)
    provider_options.append((skip_option, "skip", "Skip", "Use current .env configuration"))
    print(f"  {skip_option}. Skip - Use current .env configuration ✅")
    
    print()
    # Show warnings for invalid providers
    invalid_providers = [p for p, s in provider_summary.items() if not s["valid"]]
    if invalid_providers:
        print("⚠️  Some providers missing API keys. Check your .env file.")
    
    max_option = len(provider_options)
    
    while True:
        provider_choice = input(f"\nSelect provider (1-{max_option}, or Enter to skip): ").strip()
        if provider_choice == "" or provider_choice == skip_option:
            print("✓ Using default provider from .env")
            return None
        
        # Find selected provider
        selected_option = None
        for option_num, provider_id, display_name, description in provider_options:
            if provider_choice == option_num and provider_id != "skip":
                selected_option = (provider_id, display_name)
                break
        
        if not selected_option:
            print(f"❌ Please select 1-{max_option} or press Enter to skip.")
            continue
        
        provider_id, display_name = selected_option
        
        # Validate provider configuration
        is_valid, message = validate_provider_config(provider_id)
        if not is_valid:
            print(f"❌ {message}")
            print("Please configure the required API key in your .env file first.")
            continue
        
        print(f"✓ Selected provider: {display_name}")
        
        # Optional model selection for the provider
        model = show_model_selection_menu(provider_id)
        
        return {
            "provider": provider_id,
            "model": model
        }


def show_model_selection_menu(provider):
    """Show model selection menu for the chosen provider"""
    from src.core.llm.model_config_loader import get_model_config_loader
    
    loader = get_model_config_loader()
    models = loader.get_models_for_provider(provider)
    
    if not models:
        print(f"✓ Using default model for {provider}")
        return None
    
    print(f"\n  🎯 {provider.upper()} MODEL SELECTION:")
    print("  Available models:")
    
    model_list = []
    for i, (model_id, model_info) in enumerate(models.items(), 1):
        display_name = model_info.get("display_name", model_id)
        description = model_info.get("description", "")
        context_length = model_info.get("context_length", "Unknown")
        
        print(f"  {i}. {display_name}")
        if description:
            print(f"      {description}")
        print(f"      Context: {context_length} tokens")
        
        # Show additional info for local models
        if "size_gb" in model_info:
            size_gb = model_info["size_gb"]
            print(f"      Size: {size_gb} GB")
            
        model_list.append((model_id, display_name))
    
    print(f"  {len(model_list) + 1}. Use provider default")
    
    while True:
        choice = input(f"\nSelect model (1-{len(model_list) + 1}): ").strip()
        
        if choice == str(len(model_list) + 1) or choice == "":
            print("✓ Using provider default model")
            return None
            
        try:
            choice_int = int(choice)
            if 1 <= choice_int <= len(model_list):
                selected_model_id = model_list[choice_int - 1][0]  # Get model_id
                selected_display = model_list[choice_int - 1][1]  # Get display_name
                print(f"✓ Selected model: {selected_display}")
                return selected_model_id
            else:
                print(f"❌ Please select 1-{len(model_list) + 1}.")
        except ValueError:
            print(f"❌ Please enter a valid number (1-{len(model_list) + 1}).")


def parse_arguments():
    """Parse command line arguments"""
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
    
    parser.add_argument(
        "--project-id",
        type=str,
        required=True,
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
    
    # Language specification for new projects
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
    
    # Get dynamic provider choices from JSON configs
    try:
        from src.core.llm.model_config_loader import get_model_config_loader
        loader = get_model_config_loader()
        available_providers = loader.get_available_providers()
    except:
        available_providers = ["deepseek", "openai", "claude", "groq", "ollama"]
    
    parser.add_argument(
        "--llm-provider",
        type=str,
        choices=available_providers,
        help=f"LLM provider ({', '.join(available_providers)})"
    )
    
    parser.add_argument(
        "--llm-model",
        type=str,
        help="Specific model name for the chosen provider"
    )
    
    return parser.parse_args()


def print_banner():
    """Print welcome banner"""
    print("""
================================================================================
                         GITLAB AGENT SYSTEM
                    Automated Project Implementation
================================================================================
    
    Architecture: Supervisor Pattern with Shared State
    Agents: Planning, Coding, Testing, Review, Pipeline
    
================================================================================
    """)


async def main():
    """Main entry point with full interactive menu"""
    
    # Check if any CLI arguments were provided (for backward compatibility)
    if len(sys.argv) > 1:
        # CLI mode - use existing argument parsing
        args = parse_arguments()
        
        print_banner()
        
        # Determine mode
        if args.issue:
            mode = "single"
            print(f"Mode: Single Issue Implementation (Issue #{args.issue})")
        elif args.apply:
            mode = "implement"
            print("Mode: Full Implementation (All Issues)")
        else:
            mode = "analyze"
            print("Mode: Analysis Only (No Changes)")
        
        print(f"Project ID: {args.project_id}")
        
        # Language preferences for new projects
        tech_stack = {}
        
        # Show interactive menu if requested
        if args.menu:
            tech_stack = show_tech_stack_menu()
            if tech_stack is None:  # User cancelled
                print("[CANCELLED] Exiting...")
                return 1
        
        # Or use command line arguments
        if args.backend_lang:
            tech_stack["backend"] = args.backend_lang
            print(f"Backend Language: {args.backend_lang}")
        if args.frontend_lang:
            tech_stack["frontend"] = args.frontend_lang
            print(f"Frontend Language: {args.frontend_lang}")
        if args.database:
            tech_stack["database"] = args.database
            print(f"Database: {args.database}")
        
        if args.resume:
            resume_path = Path(args.resume)
            if not resume_path.exists():
                print(f"[ERROR] Resume file not found: {args.resume}")
                return 1
            print(f"Resuming from: {args.resume}")
        else:
            resume_path = None
        
        debug = args.debug
        project_id = args.project_id
        specific_issue = args.issue
        
        # Handle LLM provider CLI arguments
        if args.llm_provider:
            os.environ["LLM_PROVIDER"] = args.llm_provider
            print(f"LLM Provider: {args.llm_provider.upper()}")
            
            if args.llm_model:
                # Set provider-specific model environment variable
                if args.llm_provider == "deepseek":
                    os.environ["DEEPSEEK_MODEL"] = args.llm_model
                elif args.llm_provider == "openai":
                    os.environ["OPENAI_MODEL"] = args.llm_model
                elif args.llm_provider == "claude":
                    os.environ["CLAUDE_MODEL"] = args.llm_model
                elif args.llm_provider == "groq":
                    os.environ["GROQ_MODEL"] = args.llm_model
                elif args.llm_provider == "ollama":
                    os.environ["OLLAMA_MODEL"] = args.llm_model
                print(f"LLM Model: {args.llm_model}")
        
    else:
        # Interactive mode - show full menu
        config = show_main_menu()
        if config is None:
            return 1  # User cancelled
        
        print_banner()
        
        # Extract configuration
        project_id = config["project_id"]
        mode = config["mode"]
        specific_issue = config["specific_issue"]
        resume_path = config["resume_path"]
        tech_stack = config["tech_stack"]
        llm_provider = config["llm_provider"]
        debug = config["debug"]
        
        # Apply LLM provider configuration if selected
        if llm_provider:
            os.environ["LLM_PROVIDER"] = llm_provider["provider"]
            if llm_provider.get("model"):
                # Set provider-specific model environment variable
                provider = llm_provider["provider"]
                if provider == "deepseek":
                    os.environ["DEEPSEEK_MODEL"] = llm_provider["model"]
                elif provider == "openai":
                    os.environ["OPENAI_MODEL"] = llm_provider["model"]
                elif provider == "claude":
                    os.environ["CLAUDE_MODEL"] = llm_provider["model"]
                elif provider == "groq":
                    os.environ["GROQ_MODEL"] = llm_provider["model"]
                elif provider == "ollama":
                    os.environ["OLLAMA_MODEL"] = llm_provider["model"]
        
        # Show selected configuration
        if mode == "single":
            print(f"Mode: Single Issue Implementation (Issue #{specific_issue})")
        elif mode == "implement":
            print("Mode: Full Implementation (All Issues)")
        elif mode == "resume":
            print("Mode: Resume from State")
        else:
            print("Mode: Analysis Only (No Changes)")
        
        print(f"Project ID: {project_id}")
        
        if tech_stack:
            print("Tech Stack Configuration:")
            for key, value in tech_stack.items():
                print(f"  {key.title()}: {value}")
    
    print()
    
    try:
        # Run supervisor orchestrator
        await run_supervisor(
            project_id=project_id,
            mode=mode,
            specific_issue=specific_issue,
            resume_from=resume_path,
            tech_stack=tech_stack if tech_stack else None
        )
        
        print("\n[SUCCESS] Execution completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Stopped by user")
        return 130
        
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        if debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)