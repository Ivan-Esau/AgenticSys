import asyncio
import argparse
import json
from textwrap import dedent
from base_agent import BaseAgent, get_common_tools_and_client

TESTING_PROMPT = """
You are the Testing Agent.

INPUTS
- project_id, work_branch, plan_json

GOAL
- Add or improve tests for the latest changes in work_branch guided by plan_json.
- If the stack lacks a test runner, add a minimal one (keeping CI fast/deterministic).
- Update CI config if needed.

RULES
- Always include project_id in tool calls.
- Prefer fast, isolated tests; avoid network calls.
- Commit tests to work_branch.

OUTPUT
- Summary: tests added, files changed, commit IDs.
"""

async def run(project_id: str, work_branch: str, plan_json: dict | None, show_tokens: bool = True):
    tools, client = await get_common_tools_and_client()
    agent = BaseAgent("testing-agent", TESTING_PROMPT.strip(), tools)
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
    p = argparse.ArgumentParser(description="Testing Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, plan_json=None, show_tokens=not args.no_tokens))
