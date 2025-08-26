import asyncio
import argparse
from textwrap import dedent
from base_agent import BaseAgent, get_common_tools_and_client

PLANNING_PROMPT = """
You are the Planning Agent for GitLab projects.

OBJECTIVE
1) READ the project by id (issues all states, milestones, labels, wiki pages with_content=true, repo tree).
2) SYNTHESIZE:
   - OVERVIEW (scope, stakeholders, goals, risks, decisions)
   - PLAN / roadmap (near-term then medium-term; reference issue IIDs if available)
   - STRUCTURE proposal (folders + placeholder files with 1–2 line content)
3) If apply=true:
   - Create a branch from DEFAULT BRANCH (idempotent: if exists, append -v2, -v3).
   - Commit the scaffold in ONE commit using the “commit with multiple actions” pattern.
   - Write docs/OVERVIEW.md, docs/PLAN.md and docs/ORCH_PLAN.json (machine-readable plan).
   - Open an MR targeting the default branch.

RULES
- Always include `project_id` on GitLab tool calls.
- Prefer a single multi-file commit for scaffolding.
- Put plan into docs/PLAN.md and overview into docs/OVERVIEW.md.
- Use the Merge Requests API to create/annotate MRs.

OUTPUT
- End with BOTH:
  A) human-readable summary (branch name, files added, MR URL)
  B) a JSON code block:

```json PLAN
{
  "branch": "<proposed_or_created_branch>",
  "issues": [{"iid":"<iid>","title":"<title>"}],
  "structure": [{"path":"<file>","content":"<snippet>"}],
  "overview_md": "<markdown>",
  "plan_md": "<markdown>",
  "mr": {"iid": "<iid or null>", "url": "<url or null>"}
}
```
"""

async def run(project_id: str, apply: bool = False, branch_hint: str | None = None, show_tokens: bool = True):
    tools, client = await get_common_tools_and_client()
    agent = BaseAgent("planning-agent", PLANNING_PROMPT.strip(), tools)
    content = await agent.run(dedent(f"""
        project_id={project_id}
        apply={"true" if apply else "false"}
        branch_hint={branch_hint or ""}
    """), show_tokens=show_tokens)
    try:
        await client.close()
    except Exception:
        pass
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Planning Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--branch-hint", default=None)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, apply=args.apply, branch_hint=args.branch_hint, show_tokens=not args.no_tokens))
