"""
Clean modular planning agent.
Uses separated prompts, utilities, and core infrastructure.
"""

import asyncio
from textwrap import dedent
from typing import List, Any

from .utils.agent_factory import create_planning_agent
from .utils.argument_parser import (
    create_agent_parser, 
    add_planning_arguments, 
    parse_common_args
)


async def run(
    project_id: str, 
    tools: List[Any], 
    apply: bool = False, 
    branch_hint: str = None, 
    show_tokens: bool = True
):
    """
    Run planning agent with clean modular architecture.
    
    Args:
        project_id: GitLab project ID
        tools: Tools available to the agent
        apply: Whether to apply changes (create branches/files)
        branch_hint: Optional branch naming hint
        show_tokens: Whether to show token streaming
        
    Returns:
        Agent response content
    """
    # Create agent using factory
    agent = create_planning_agent(tools, project_id)
    
    # Execute with clean input format
    content = await agent.run(dedent(f"""
        project_id={project_id}
        apply={"true" if apply else "false"}
        branch_hint={branch_hint or ""}
    """), show_tokens=show_tokens)
    
    return content


def main():
    """Command-line entry point using standardized argument parsing."""
    # Create parser with planning-specific arguments
    parser = create_agent_parser("planning", "Planning Agent")
    parser = add_planning_arguments(parser)
    args = parser.parse_args()
    
    # Extract common arguments
    common_args = parse_common_args(args)
    
    # Run the agent
    asyncio.run(run(
        project_id=common_args["project_id"],
        tools=[],  # Tools will be provided by supervisor in practice
        apply=args.apply,
        branch_hint=args.branch_hint,
        show_tokens=common_args["show_tokens"]
    ))


if __name__ == "__main__":
    main()