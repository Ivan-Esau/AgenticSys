import asyncio
import argparse
import json
from textwrap import dedent
from base_agent import BaseAgent, get_common_tools_and_client

REVIEW_PROMPT = """
You are the Review Agent.

INPUTS
- project_id, work_branch, plan_json

GOAL
- If an MR for work_branch does not exist, create one targeting DEFAULT BRANCH with a clear title/description.
- Post a succinct review (link to issues), ensure CI passes.
- Approve and MERGE the MR (delete source branch on merge if supported).
- If merge/approve tools are unavailable, leave a review and enable auto-merge when pipeline succeeds.

RULES
- Always include project_id in tool calls.
- Prefer squash merge if project policy enforces it.

OUTPUT
- MR IID/URL, merged status, whether source branch was deleted.
"""

async def run(project_id: str, work_branch: str, plan_json: dict | None, show_tokens: bool = True):
    tools, client = await get_common_tools_and_client()
    agent = BaseAgent("review-agent", REVIEW_PROMPT.strip(), tools)
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true
    """), show_tokens=show_tokens)
    try:
        await client.close()
    except Exception:
        pass
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Review Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, plan_json=None, show_tokens=not args.no_tokens))
