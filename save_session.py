#!/usr/bin/env python3
"""
Session state saver for AgenticSys project.
Captures current state for easy restoration in future Claude sessions.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path


def save_session_state():
    """Save current session state to a JSON file."""

    session_data = {
        "timestamp": datetime.now().isoformat(),
        "project": "AgenticSys",
        "current_branch": get_git_branch(),
        "latest_commit": get_latest_commit(),
        "key_files_modified": get_modified_files(),
        "work_completed": [
            "Pipeline waiting issue fixed",
            "Supervisor refactored to modular architecture",
            "Agent prompts enhanced with strict pipeline rules",
            "commit_message parameter documentation added"
        ],
        "active_issues": {
            "issue_2": "Implementation may need retry with fixed prompts",
            "pipeline_monitoring": "Needs testing with slow runners",
            "java_project": "TaskTest.testToString failure needs fixing"
        },
        "test_project": {
            "gitlab_id": "150",
            "name": "PM10",
            "type": "Java/Maven",
            "branch": "master",
            "last_pipeline": "4259",
            "failing_test": "TaskTest.testToString"
        },
        "configuration": {
            "llm_provider": "DeepSeek",
            "model": "deepseek-chat",
            "tech_stack": {
                "backend": "java",
                "frontend": "html-css-js"
            }
        },
        "important_patterns": {
            "pipeline_tracking": "MY_PIPELINE_ID = #XXXX",
            "commit_syntax": 'create_or_update_file(ref=branch, commit_message="msg", ...)',
            "completion_signal": "TESTING_PHASE_COMPLETE: Issue #X tests finished..."
        }
    }

    # Save to file
    output_file = Path("docs/session_state.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(session_data, f, indent=2)

    print(f"[SUCCESS] Session state saved to {output_file}")
    return output_file


def get_git_branch():
    """Get current git branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except:
        return "unknown"


def get_latest_commit():
    """Get latest commit hash and message."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--oneline"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except:
        return "unknown"


def get_modified_files():
    """Get list of recently modified files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~5..HEAD"],
            capture_output=True,
            text=True
        )
        files = result.stdout.strip().split('\n')
        return [f for f in files if f][:10]  # Top 10 files
    except:
        return []


if __name__ == "__main__":
    save_session_state()

    print("\n[INFO] To restore this session in Claude:")
    print("1. Upload docs/SESSION_CONTEXT.md")
    print("2. Upload docs/session_state.json")
    print("3. Say: 'Continue from the saved session context'")
    print("\n[TIP] Claude will have full context of your work!")