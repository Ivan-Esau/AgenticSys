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

from src.orchestrator.supervisor import run_supervisor


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="GitLab Agent System - Automated Project Implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze project (no changes):
  python run.py --project-id 113
  
  # Full implementation (all issues):
  python run.py --project-id 113 --apply
  
  # Implement single issue:
  python run.py --project-id 113 --issue 1 --apply
  
  # Resume from saved state:
  python run.py --project-id 113 --resume state_113_20240826.json --apply
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
    """Main entry point"""
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
    
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            print(f"[ERROR] Resume file not found: {args.resume}")
            return 1
        print(f"Resuming from: {args.resume}")
    else:
        resume_path = None
    
    print()
    
    try:
        # Run supervisor orchestrator
        await run_supervisor(
            project_id=args.project_id,
            mode=mode,
            specific_issue=args.issue,
            resume_from=resume_path
        )
        
        print("\n[SUCCESS] Execution completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Stopped by user")
        return 130
        
    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)