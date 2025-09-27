#!/usr/bin/env python3
"""
Migration script to switch to refactored supervisor.
This script helps transition from the monolithic supervisor.py to the new modular structure.
"""

import os
import shutil
from pathlib import Path


def main():
    """Main migration function"""
    print("="*60)
    print("SUPERVISOR REFACTORING MIGRATION")
    print("="*60)
    print()

    orchestrator_dir = Path("src/orchestrator")

    # Check if refactored version exists
    refactored_file = orchestrator_dir / "supervisor_refactored.py"
    original_file = orchestrator_dir / "supervisor.py"
    backup_file = orchestrator_dir / "supervisor_original.py"

    if not refactored_file.exists():
        print("❌ Refactored supervisor not found!")
        print(f"   Expected at: {refactored_file}")
        return 1

    # Check new modules exist
    required_modules = [
        "issue_manager.py",
        "pipeline_manager.py",
        "planning_manager.py",
        "mcp_integration.py"
    ]

    missing_modules = []
    for module in required_modules:
        module_path = orchestrator_dir / module
        if not module_path.exists():
            missing_modules.append(module)

    if missing_modules:
        print("❌ Missing required modules:")
        for module in missing_modules:
            print(f"   - {module}")
        return 1

    print("✅ All required modules found")
    print()

    # Offer to backup original
    if original_file.exists():
        print("📁 Current supervisor.py found")

        if backup_file.exists():
            print("⚠️  Backup already exists at supervisor_original.py")
            response = input("   Overwrite backup? (y/N): ").strip().lower()
            if response != 'y':
                print("   Keeping existing backup")
            else:
                shutil.copy2(original_file, backup_file)
                print("✅ Backup updated")
        else:
            shutil.copy2(original_file, backup_file)
            print("✅ Original backed up to supervisor_original.py")

    # Replace supervisor.py with refactored version
    print()
    print("🔄 Switching to refactored supervisor...")

    try:
        # Copy refactored to supervisor.py
        shutil.copy2(refactored_file, original_file)
        print("✅ Refactored supervisor activated")

        # Update run.py import if needed
        run_py = Path("run.py")
        if run_py.exists():
            content = run_py.read_text()

            # Check if import needs updating
            if "from src.orchestrator.supervisor import run_supervisor" in content:
                print("✅ run.py already uses correct import")
            elif "from src.orchestrator.supervisor_refactored import run_supervisor" in content:
                # Update to use main supervisor
                new_content = content.replace(
                    "from src.orchestrator.supervisor_refactored import run_supervisor",
                    "from src.orchestrator.supervisor import run_supervisor"
                )
                run_py.write_text(new_content)
                print("✅ Updated run.py import")

        print()
        print("="*60)
        print("MIGRATION COMPLETE!")
        print("="*60)
        print()
        print("The refactored supervisor is now active with:")
        print("  • Modular architecture")
        print("  • Separated concerns")
        print("  • Better maintainability")
        print("  • Improved error handling")
        print()
        print("New modules:")
        print("  • issue_manager.py - Issue tracking and validation")
        print("  • pipeline_manager.py - CI/CD pipeline operations")
        print("  • planning_manager.py - Planning and prioritization")
        print("  • mcp_integration.py - MCP server interactions")
        print()
        print("To revert if needed:")
        print("  cp src/orchestrator/supervisor_original.py src/orchestrator/supervisor.py")
        print()

        return 0

    except Exception as e:
        print(f"❌ Migration failed: {e}")

        # Try to restore from backup
        if backup_file.exists():
            print("🔄 Attempting to restore from backup...")
            try:
                shutil.copy2(backup_file, original_file)
                print("✅ Original supervisor restored")
            except Exception as restore_error:
                print(f"❌ Failed to restore: {restore_error}")

        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())