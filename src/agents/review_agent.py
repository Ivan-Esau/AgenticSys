"""
Clean modular review agent.
Uses separated prompts, utilities, and core infrastructure.
"""

import asyncio
import json
from textwrap import dedent
from typing import List, Any, Dict, Optional

from .utils.agent_factory import create_review_agent
from .utils.argument_parser import (
    create_agent_parser, 
    add_review_arguments, 
    parse_common_args
)


async def run(
    project_id: str,
    work_branch: str,
    plan_json: Optional[Dict] = None,
    tools: List[Any] = None,
    show_tokens: bool = True
):
    """
    Run review agent with clean modular architecture.
    
    Args:
        project_id: GitLab project ID
        work_branch: Branch to review and merge
        plan_json: Planning JSON with review context
        tools: Tools available to the agent
        show_tokens: Whether to show token streaming
        
    Returns:
        Agent response content
    """
    if tools is None:
        tools = []
    
    # Create agent using factory
    agent = create_review_agent(tools, project_id)
    
    # Execute with clean input format
    content = await agent.run(dedent(f"""
        project_id={project_id}
        work_branch={work_branch}
        plan_json={json.dumps(plan_json or {}, ensure_ascii=False)}
        apply=true
    """), show_tokens=show_tokens)
    
    return content


def main():
    """Command-line entry point using standardized argument parsing."""
    # Create parser with review-specific arguments
    parser = create_agent_parser("review", "Review Agent")
    parser = add_review_arguments(parser)
    args = parser.parse_args()
    
    # Extract common arguments
    common_args = parse_common_args(args)
    
    # Run the agent
    asyncio.run(run(
        project_id=common_args["project_id"],
        work_branch=args.work_branch,
        plan_json=None,  # Would be provided by supervisor in practice
        tools=[],  # Tools will be provided by supervisor in practice
        show_tokens=common_args["show_tokens"]
    ))


if __name__ == "__main__":
    main()