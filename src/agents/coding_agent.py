import asyncio
import argparse
import json
from textwrap import dedent

# Import from new modules
try:
    from .base_agent import BaseAgent, get_common_tools_and_client
    from src.core.llm.config import Config
    from src.core.agents.constants import AGENT_NAMES
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
   - CHECK TECH STACK: Use get_project_context to see if languages are specified
   - ANALYZE: Determine if file has real implementation or just placeholders
   - DECIDE: Based on implementation_status in plan
     * "complete": Skip or only add minor improvements
     * "partial": Read existing code, preserve it, add missing parts
     * "not_started": Implement from scratch using specified or detected language

2) PRESERVE EXISTING FUNCTIONALITY:
   - NEVER delete or overwrite working code
   - ADD to existing code, don't replace it
   - If unsure, create new methods/classes alongside existing ones
   - Use descriptive names to avoid conflicts (e.g., EnhancedGameLoop vs GameLoop)

3) ISSUE-BASED BRANCH MANAGEMENT:
   - FIRST: Check if work_branch exists using list_branches
   - If work_branch doesn't exist:
     * Extract issue IID from issues list (look for #123 pattern)
     * Create descriptive branch name: "feature/issue-{iid}-{description-slug}"
     * Create branch from DEFAULT BRANCH using create_branch
     * Update issue status to "in_progress" using update_issue
   - If work_branch exists: Use it as-is
   
4) IMPLEMENTATION STRATEGY:
   - Read ALL files mentioned in plan before starting
   - LANGUAGE SELECTION PRIORITY:
     * If tech_stack specified in context: USE specified backend/frontend languages
     * If existing files exist: MATCH existing file extensions and patterns
     * Default fallback: Choose appropriate language based on project type
   - For partial implementations:
     * Keep existing class structure
     * Add missing methods
     * Enhance existing methods without breaking them
   - Commit messages should be specific: "feat: Add pause functionality to existing GameLoop"

CRITICAL ISSUE MANAGEMENT RULES:
- Always include project_id in tool calls
- FIRST ACTION: Check if work_branch exists, create from issue if needed
- Extract issue IID from issues parameter (#123 format)
- Update issue status to "in_progress" when starting work
- Use GitLab tools: list_branches, create_branch, update_issue
- Branch naming: "feature/issue-{iid}-{slug}" or "bugfix/issue-{iid}-{slug}"
- Link commits to issues: "feat: implement user auth (#123)"

IMPLEMENTATION RULES:
- ALWAYS read before writing
- Keep commits focused - one feature per commit  
- If existing code conflicts with plan, document it in commit message
- Write docs/IMPLEMENTATION_NOTES.md if you find unexpected existing code
- DO NOT WRITE TESTS - The Testing Agent handles all test files
- Focus ONLY on source code implementation (src/ directory)
- Signal completion clearly when implementation is done

OUTPUT
- Summary: issues addressed, existing code preserved, new functionality added, files modified
- Status: "IMPLEMENTATION COMPLETE" when done (for Testing Agent handoff)
"""

async def run(project_id: str, work_branch: str, issues: list[str], plan_json: dict | None, tools: List[Any], show_tokens: bool = True, fix_mode: bool = False, error_context: str = ""):
    """Run coding agent with provided tools (no MCP client management needed)"""
    agent = BaseAgent("coding-agent", CODING_PROMPT.strip(), tools, project_id=project_id)
    issues_list = " | ".join(issues) if issues else ""
    fix_context = f"\nfix_mode={fix_mode}\nerror_context={error_context}" if fix_mode else ""
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        issues=[{issues_list}]
        apply=true{fix_context}
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
