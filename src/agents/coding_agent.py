import asyncio
import argparse
import json
from textwrap import dedent

# Import from new modules
try:
    from .base_agent import BaseAgent, get_common_tools_and_client
    from ..core.config import Config
    from ..core.constants import AGENT_NAMES
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.agents.base_agent import BaseAgent
from typing import List, Any

CODING_PROMPT = """
You are the Coding Agent - responsible for implementing features while preserving existing code.

INPUTS
- project_id, work_branch
- plan_json: JSON with keys branch, issues[], structure[], overview_md, plan_md
  * issues may include: implementation_status, existing_code_analysis, files_to_modify

CRITICAL: ANALYZE BEFORE IMPLEMENTING
1) For EACH file you need to modify or create:
   - FIRST: Use get_file_contents to check if it exists and what it contains
   - ANALYZE: Determine if file has real implementation or just placeholders
   - DECIDE: Based on implementation_status in plan
     * "complete": Skip or only add minor improvements
     * "partial": Read existing code, preserve it, add missing parts
     * "not_started": Implement from scratch

2) PRESERVE EXISTING FUNCTIONALITY:
   - NEVER delete or overwrite working code
   - ADD to existing code, don't replace it
   - If unsure, create new methods/classes alongside existing ones
   - Use descriptive names to avoid conflicts (e.g., EnhancedGameLoop vs GameLoop)

3) IMPLEMENTATION STRATEGY:
   - Ensure branch exists (create from DEFAULT BRANCH if missing)
   - Read ALL files mentioned in plan before starting
   - For partial implementations:
     * Keep existing class structure
     * Add missing methods
     * Enhance existing methods without breaking them
   - Commit messages should be specific: "feat: Add pause functionality to existing GameLoop"

RULES
- Always include project_id in tool calls
- ALWAYS read before writing
- Keep commits focused - one feature per commit
- If existing code conflicts with plan, document it in commit message
- Write docs/IMPLEMENTATION_NOTES.md if you find unexpected existing code

OUTPUT
- Summary: issues addressed, existing code preserved, new functionality added, files modified
"""

async def run(project_id: str, work_branch: str, issues: list[str], plan_json: dict | None, tools: List[Any], show_tokens: bool = True):
    """Run coding agent with provided tools (no MCP client management needed)"""
    agent = BaseAgent("coding-agent", CODING_PROMPT.strip(), tools, project_id=project_id)
    issues_list = " | ".join(issues) if issues else ""
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        issues=[{issues_list}]
        apply=true
    """), show_tokens=show_tokens)
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Coding Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--issues", nargs="*", default=[])
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, args.issues, plan_json=None, show_tokens=not args.no_tokens))
