"""
Clean modular review agent.
Uses separated prompts, utilities, and core infrastructure.
"""

import json
from textwrap import dedent
from typing import List, Any, Dict, Optional

from .utils.agent_factory import create_review_agent


async def run(
    project_id: str,
    work_branch: str,
    plan_json: Optional[Dict] = None,
    tools: List[Any] = None,
    show_tokens: bool = True,
    pipeline_config: dict = None
):
    """
    Run review agent with clean modular architecture.
    
    Args:
        project_id: GitLab project ID
        work_branch: Branch to review and merge
        plan_json: Planning JSON with review context
        tools: Tools available to the agent
        show_tokens: Whether to show token streaming
        pipeline_config: Pipeline configuration for tech stack
        
    Returns:
        Agent response content
    """
    if tools is None:
        tools = []
    
    # Create agent using factory with pipeline config
    agent = create_review_agent(tools, project_id, pipeline_config)
    
    # Execute with clean input format
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true
    """), show_tokens=show_tokens)
    
    return content