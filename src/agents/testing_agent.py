import asyncio
import argparse
import json
from textwrap import dedent
from typing import List, Any

# Import from new modules
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.agents.base_agent import BaseAgent


TESTING_PROMPT = """
You are the Testing Agent - responsible for testing while preserving existing test suites.

INPUTS
- project_id, work_branch, plan_json

CRITICAL: ANALYZE EXISTING TESTS FIRST
1) CHECK for existing test files:
   - Use get_file_contents on test directories
   - Identify test framework (Jest, Mocha, pytest, etc.)
   - Check test coverage of existing functionality

2) PRESERVE AND ENHANCE:
   - NEVER delete existing working tests
   - ADD new tests for new functionality
   - ENHANCE existing tests if they're incomplete
   - If test file exists:
     * Read it first
     * Add new test cases to existing describe/test blocks
     * Keep consistent style with existing tests

3) TEST STRATEGY:
   - For new code: Write comprehensive tests
   - For modified code: Update tests to match changes
   - For existing code: Only add missing test cases
   - Ensure tests actually run (check package.json or test config)

RULES
- Always include project_id in tool calls
- ALWAYS read existing tests before writing new ones
- Match the testing style/framework already in use
- Don't change test runner unless absolutely necessary
- Prefer isolated unit tests over integration tests
- Commit message: "test: Add tests for [specific feature]"

OUTPUT
- Summary: existing tests preserved, new tests added, coverage improved
"""

async def run(project_id: str, work_branch: str, plan_json: dict | None, tools: List[Any], show_tokens: bool = True):
    """Run testing-agent with provided tools (no MCP client management needed)"""
    agent = BaseAgent("testing-agent", TESTING_PROMPT.strip(), tools, project_id=project_id)
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true
    """), show_tokens=show_tokens)
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Testing Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, plan_json=None, show_tokens=not args.no_tokens))
