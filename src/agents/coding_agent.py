"""
Clean modular coding agent.
Uses separated prompts, utilities, and core infrastructure.
"""

import json
from textwrap import dedent
from typing import List, Any, Dict, Optional

from .utils.agent_factory import create_coding_agent


async def run(
    project_id: str,
    work_branch: str,
    issues: List[str],
    plan_json: Optional[Dict] = None,
    tools: List[Any] = None,
    show_tokens: bool = True,
    fix_mode: bool = False,
    error_context: str = "",
    pipeline_config: dict = None
):
    """
    Run coding agent with clean modular architecture.

    Args:
        project_id: GitLab project ID
        work_branch: Branch to work on
        issues: List of issues to implement
        plan_json: Planning JSON with implementation details
        tools: Tools available to the agent
        show_tokens: Whether to show token streaming
        fix_mode: Whether running in pipeline fix mode
        error_context: Error context for fix mode
        pipeline_config: Pipeline configuration for tech stack

    Returns:
        Agent response content
    """
    if tools is None:
        tools = []

    # Create agent using factory with pipeline config
    agent = create_coding_agent(tools, project_id, pipeline_config)
    
    # Format issues for agent
    issues_list = " | ".join(issues) if issues else ""
    fix_context = f"\nfix_mode={fix_mode}\nerror_context={error_context}" if fix_mode else ""
    
    # Execute with clean input format
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        issues=[{issues_list}]
        apply=true{fix_context}
    """), show_tokens=show_tokens)

    return content