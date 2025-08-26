import asyncio
import time
import json
import argparse
from textwrap import dedent

from base_agent import get_common_tools_and_client, BaseAgent, extract_json_block
import planning_agent, coding_agent, testing_agent, review_agent

def branch_name(prefix="orchestrator"):
    ts = time.strftime("%Y%m%d-%H%M%S")
    return f"{prefix}/{ts}"

ORCH_BANNER = """
╔══════════════════════════════════════════════════════════════╗
║                 Orchestrator Agent (GitLab)                  ║
╚══════════════════════════════════════════════════════════════╝
"""

async def fetch_plan_json_from_repo(project_id: str, ref: str, tools) -> dict | None:
    """
    Fallback: read docs/ORCH_PLAN.json from the repo via MCP 'get_file_contents'.
    """
    util = BaseAgent(
        "utility-get-plan",
        "Call get_file_contents(project_id, file_path='docs/ORCH_PLAN.json', ref=REF) and return only the raw file content.",
        tools,
    )
    out = await util.run(dedent(f"""
        project_id={project_id}
        file_path=docs/ORCH_PLAN.json
        ref={ref}
        apply=false
    """), show_tokens=False)
    try:
        return json.loads(out) if out else None
    except Exception:
        return None

async def list_open_issues_text(project_id: str, tools) -> str:
    util = BaseAgent(
        "utility-list-issues",
        "Call list_issues(project_id, state='opened') and print one line per issue as '#{iid} | {title}'.",
        tools,
    )
    return await util.run(f"project_id={project_id} state=opened apply=false", show_tokens=False) or ""

async def main(project_id: str, apply: bool, choose_first_n: int, show_tokens: bool):
    print(ORCH_BANNER)
    tools, client = await get_common_tools_and_client()

    # 1) Planning (writes if --apply is passed)
    print(f"\n▶ Step 1/4: Planning / analysis ({'writes enabled' if apply else 'no writes'})")
    plan_text = await planning_agent.run(project_id, apply=apply, branch_hint=None, show_tokens=show_tokens)

    # Extract the machine-readable plan JSON from the planner's output
    plan_json = extract_json_block(plan_text or "")
    work_branch = plan_json.get("branch") if plan_json else None

    # If planner wrote but didn't include JSON in the message, try to read docs/ORCH_PLAN.json
    if not plan_json and apply and work_branch:
        plan_json = await fetch_plan_json_from_repo(project_id, work_branch, tools)

    # 2) Select issues (from plan, or fallback to first N open issues)
    if plan_json and plan_json.get("issues"):
        print("\n▶ Step 2/4: Issues from plan")
        selected = [f"#{i.get('iid')} | {i.get('title')}" for i in plan_json["issues"]][:choose_first_n]
        for s in selected:
            print("  " + s)
    else:
        print("\n▶ Step 2/4: Selecting issues (fallback)")
        issues_text = await list_open_issues_text(project_id, tools)
        raw_lines = [ln.strip() for ln in issues_text.splitlines() if ln.strip().startswith("#")]
        selected = raw_lines[:choose_first_n]
        if not selected:
            print("  No open issues found. Proceeding with scaffold/tests only.")

    # 3) Coding + Testing on a dedicated branch
    if not work_branch:
        work_branch = branch_name()

    print(f"\n▶ Step 3/4: Coding on branch '{work_branch}'")
    await coding_agent.run(project_id, work_branch, selected, plan_json, show_tokens=show_tokens)

    print(f"\n▶ Step 3b/4: Testing on branch '{work_branch}'")
    await testing_agent.run(project_id, work_branch, plan_json, show_tokens=show_tokens)

    # 4) Review & Merge (close branch)
    print(f"\n▶ Step 4/4: Review & merge (close '{work_branch}')")
    await review_agent.run(project_id, work_branch, plan_json, show_tokens=show_tokens)

    try:
        await client.close()
    except Exception:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Orchestrator Agent (planning, coding, testing, review)")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Enable writes (branches/commits/MRs). If omitted, planner runs read-only.")
    parser.add_argument("--issues", type=int, default=2, help="How many issues to implement if the plan lacks issues")
    parser.add_argument("--no-tokens", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.project_id, apply=args.apply, choose_first_n=args.issues, show_tokens=not args.no_tokens))
