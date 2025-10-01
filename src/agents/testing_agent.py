"""
Clean modular testing agent.
Uses separated prompts, utilities, and core infrastructure.
"""

import json
from textwrap import dedent
from typing import List, Any, Dict, Optional

from .utils.agent_factory import create_testing_agent


async def run(
    project_id: str,
    work_branch: str,
    plan_json: Optional[Dict] = None,
    tools: List[Any] = None,
    show_tokens: bool = True,
    fix_mode: bool = False,
    error_context: str = "",
    pipeline_config: dict = None,
    output_callback=None
):
    """
    Run testing agent with clean modular architecture.

    Args:
        project_id: GitLab project ID
        work_branch: Branch to test
        plan_json: Planning JSON with test details
        tools: Tools available to the agent
        show_tokens: Whether to show token streaming
        fix_mode: Whether running in pipeline fix mode
        error_context: Error context for fix mode
        pipeline_config: Pipeline configuration for tech stack
        output_callback: Optional callback for WebSocket output

    Returns:
        Agent response content
    """
    if tools is None:
        tools = []

    # Create agent using factory with pipeline config
    agent = create_testing_agent(tools, project_id, pipeline_config, output_callback)
    
    # Prepare context for fix mode
    fix_context = f"\nfix_mode={fix_mode}\nerror_context={error_context}" if fix_mode else ""
    
    # Execute with clean input format
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true{fix_context}
    """), show_tokens=show_tokens)
    
    return content