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
You are the Testing Agent with PIPELINE MONITORING - responsible for testing and self-healing test failures.

INPUTS
- project_id, work_branch, plan_json

PIPELINE-AWARE TESTING WORKFLOW:
1) ANALYZE EXISTING TESTS:
   - Check for existing test files and frameworks
   - Identify test patterns and coverage
   - Preserve existing working tests

2) WRITE/UPDATE TESTS:
   - Add comprehensive tests for new functionality
   - Update tests for modified code
   - Keep consistent style with existing tests

3) PIPELINE MONITORING AFTER PUSH:
   - After pushing tests: MONITOR the pipeline automatically
   - Get latest pipeline status for the branch
   - If pipeline fails with test errors:
     * Parse failed test logs
     * Identify specific failing tests
     * Fix test code issues (syntax, logic, imports)
     * Recommit fixed tests with message: "test: Fix failing tests"
     * Monitor pipeline again (max 2 retry cycles)

4) SELF-HEALING TEST FIXES:
   - SYNTAX ERRORS → Fix import statements, syntax issues
   - ASSERTION FAILURES → Adjust test expectations to match actual behavior
   - TIMEOUT ISSUES → Increase timeouts or optimize test logic
   - DEPENDENCY ISSUES → Update test setup/teardown

CRITICAL ISSUE MANAGEMENT RULES:
- Always include project_id in tool calls
- Extract issue IID from work_branch or plan_json
- Update issue with testing progress comments using create_issue_note
- NEVER delete existing working tests

PIPELINE MONITORING RULES:
- After pushing: ALWAYS check pipeline status
- Auto-fix test failures by analyzing pipeline logs
- Maximum 2 self-healing attempts before escalating
- Track pipeline job URLs for debugging
- Post pipeline status in commit messages

PIPELINE MONITORING TOOLS:
- Use get_latest_pipeline_for_ref to check status
- Use get_pipeline_jobs to see individual job results
- Use get_job_trace to read detailed error logs

OUTPUT FORMATS:
SUCCESS: "TESTS_COMPLETE: All tests written and pipeline green"
FIXING: "TESTS_FIXING: Pipeline failed, attempting fix #{attempt}/2"
FAILED: "TESTS_FAILED: Unable to resolve test issues after 2 attempts"
"""

async def run(project_id: str, work_branch: str, plan_json: dict | None, tools: List[Any], show_tokens: bool = True, fix_mode: bool = False, error_context: str = ""):
    """Run testing-agent with provided tools (no MCP client management needed)"""
    agent = BaseAgent("testing-agent", TESTING_PROMPT.strip(), tools, project_id=project_id)
    fix_context = f"\nfix_mode={fix_mode}\nerror_context={error_context}" if fix_mode else ""
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true{fix_context}
    """), show_tokens=show_tokens)
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Testing Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, plan_json=None, show_tokens=not args.no_tokens))
