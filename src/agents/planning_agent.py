"""
Clean modular planning agent.
Uses separated prompts, utilities, and core infrastructure.
"""

from textwrap import dedent
from typing import List, Any

from .utils.agent_factory import create_planning_agent


async def run(
    project_id: str,
    tools: List[Any],
    apply: bool = False,
    branch_hint: str = None,
    show_tokens: bool = True,
    pipeline_config: dict = None
):
    """
    Run planning agent with clean modular architecture.

    Args:
        project_id: GitLab project ID
        tools: Tools available to the agent
        apply: Whether to apply changes (create branches/files)
        branch_hint: Optional branch naming hint
        show_tokens: Whether to show token streaming
        pipeline_config: Pipeline configuration for tech stack

    Returns:
        Agent response content
    """
    # Create agent using factory with pipeline config
    agent = create_planning_agent(tools, project_id, pipeline_config)
    
    # Execute with clean input format
    content = await agent.run(dedent(f"""
        project_id={project_id}
        apply={"true" if apply else "false"}
        branch_hint={branch_hint or ""}
    """), show_tokens=show_tokens)
    
    return content