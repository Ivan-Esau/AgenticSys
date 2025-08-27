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


REVIEW_PROMPT = """
You are the Review Agent responsible for merging code.

INPUTS
- project_id, work_branch, plan_json

GOAL
- First CHECK if an MR already exists for work_branch (list_merge_requests with source_branch filter).
- If MR exists: Use its IID to merge it immediately.
- If no MR: Create one targeting DEFAULT BRANCH with clear title/description.
- IMMEDIATELY MERGE using merge_merge_request tool with merge_when_pipeline_succeeds=false.
- Delete source branch after merge (should_remove_source_branch=true).

IMPORTANT RULES
- Always include project_id in tool calls.
- DO NOT wait for CI/CD pipelines - merge immediately.
- Use merge_when_pipeline_succeeds=false or skip pipeline checks.
- If normal merge fails, try with skip_ci or force merge options.
- Prefer squash merge if available.

OUTPUT
- MR IID/URL, merged status (must be true), source branch deletion status.
"""

async def run(project_id: str, work_branch: str, plan_json: dict | None, tools: List[Any], show_tokens: bool = True):
    """Run review-agent with provided tools (no MCP client management needed)"""
    agent = BaseAgent("review-agent", REVIEW_PROMPT.strip(), tools, project_id=project_id)
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true
    """), show_tokens=show_tokens)
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Review Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--work-branch", required=True)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.work_branch, plan_json=None, show_tokens=not args.no_tokens))
