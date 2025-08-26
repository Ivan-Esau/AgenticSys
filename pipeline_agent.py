import asyncio
import argparse
from textwrap import dedent
from base_agent import BaseAgent, get_common_tools_and_client

PIPELINE_PROMPT = """
You are the Pipeline Watcher Agent.

INPUTS
- project_id
- ref (branch name) OR mr_iid

GOAL
1) Determine the source branch/ref:
   - If mr_iid is provided, get the MR and use its source branch.
   - Else use the given ref.
2) Fetch the LATEST pipeline for that ref. If none, report 'no pipeline found'.
3) If the pipeline status != 'success':
   - List failed jobs (name, URL).
   - Include the first error line from each job log if accessible.
   - Post/Update an MR note titled "CI Summary" with status and bullets (if mr_iid known).
4) If all jobs green, comment "All checks passed ✅" on the MR (if mr_iid provided).

RULES
- Always include project_id on GitLab tool calls.
- Use endpoints that map to: latest pipeline for ref, list pipeline jobs, MR notes.

OUTPUT
- A concise summary including pipeline id, status, and any failed jobs.
"""

async def run(project_id: str, ref: str | None, mr_iid: str | None, show_tokens: bool = True):
    tools, client = await get_common_tools_and_client()
    agent = BaseAgent("pipeline-agent", PIPELINE_PROMPT.strip(), tools)
    ref_str = ref or ""
    mr_str = mr_iid or ""
    content = await agent.run(dedent(f"""
        project_id={project_id}
        ref={ref_str}
        mr_iid={mr_str}
        apply=true
    """), show_tokens=show_tokens)
    try:
        await client.close()
    except Exception:
        pass
    return content

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Pipeline Watcher Agent")
    p.add_argument("--project-id", required=True)
    p.add_argument("--ref", default=None)
    p.add_argument("--mr-iid", default=None)
    p.add_argument("--no-tokens", action="store_true")
    args = p.parse_args()
    asyncio.run(run(args.project_id, args.ref, args.mr_iid, show_tokens=not args.no_tokens))
