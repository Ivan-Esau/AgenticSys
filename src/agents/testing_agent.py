"""
Clean modular testing agent.
Uses separated prompts, utilities, and core infrastructure.
"""

import asyncio
import json
from textwrap import dedent
from typing import List, Any, Dict, Optional

from .utils.agent_factory import create_testing_agent
from .utils.argument_parser import (
    create_agent_parser, 
    add_testing_arguments, 
    parse_common_args
)


async def run(
    project_id: str,
    work_branch: str,
    plan_json: Optional[Dict] = None,
    tools: List[Any] = None,
    show_tokens: bool = True,
    fix_mode: bool = False,
    error_context: str = ""
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
        
    Returns:
        Agent response content
    """
    if tools is None:
        tools = []
    
    # Create agent using factory
    agent = create_testing_agent(tools, project_id)
    
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


def main():
    """Command-line entry point using standardized argument parsing."""
    # Create parser with testing-specific arguments
    parser = create_agent_parser("testing", "Testing Agent")
    parser = add_testing_arguments(parser)
    args = parser.parse_args()
    
    # Extract common arguments
    common_args = parse_common_args(args)
    
    # Run the agent
    asyncio.run(run(
        project_id=common_args["project_id"],
        work_branch=args.work_branch,
        plan_json=None,  # Would be provided by supervisor in practice
        tools=[],  # Tools will be provided by supervisor in practice
        show_tokens=common_args["show_tokens"],
        fix_mode=args.fix_mode,
        error_context=args.error_context
    ))


if __name__ == "__main__":
    main()