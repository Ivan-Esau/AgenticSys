import asyncio
import argparse
import json
from textwrap import dedent
from base_agent import BaseAgent, get_common_tools_and_client

CODING_PROMPT = """
You are the Coding Agent.

INPUTS
- project_id, work_branch
- plan_json: JSON with keys branch, issues[], structure[], overview_md, plan_md

GOAL
- Ensure branch exists (create from DEFAULT BRANCH if missing).
- Implement code and files guided by plan_json.structure and referenced issues.
- Use the Commits API with multiple actions. Commit messages reference issues (e.g., "feat: X (closes #{iid})").
- Update configs/tests as needed for the current stack.

RULES
- Always include project_id in tool calls.
- Keep commits small and readable.
- If something is unclear, write docs/QUESTIONS.md with assumptions and follow-ups.

OUTPUT
- Summary: issues addressed, files touched, commit IDs, branch.
"""

async def run(project_id: str, work_branch: str, issues: list[str], plan_json: dict | None, show_tokens: bool = True):
    tools, client = await get_common_tools_and_client()
    agent = BaseAgent("coding-agent", CODING_PROMPT.strip(), tools)
    issues_list = " | ".join(issues) if issues else ""
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        issues=[{issues_list}]
        apply=true
    """), show_tokens=show_tokens)
    try:
        await client.close()
    except Exception:
        pass
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Coding Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--issues", nargs="*", default=[])
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, args.issues, plan_json=None, show_tokens=not args.no_tokens))
