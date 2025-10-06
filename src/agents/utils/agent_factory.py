"""
Agent factory for standardized agent creation.
Provides consistent agent setup and configuration.
"""

from typing import List, Any, Optional, Callable, Awaitable, Dict
from ..base_agent import BaseAgent


def create_agent(
    name: str,
    system_prompt: str,
    tools: List[Any],
    project_id: Optional[str] = None,
    model: Optional[Any] = None,
    output_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> BaseAgent:
    """
    Create a standardized agent with consistent configuration.

    Args:
        name: Agent name (e.g., 'planning-agent')
        system_prompt: System prompt for the agent
        tools: List of tools available to the agent
        project_id: Optional project ID for state management
        model: Optional model override
        output_callback: Optional callback for WebSocket output

    Returns:
        Configured BaseAgent instance
    """
    return BaseAgent(
        name=name,
        system_prompt=system_prompt,
        tools=tools,
        model=model,
        project_id=project_id,
        output_callback=output_callback
    )


def create_planning_agent(
    tools: List[Any],
    project_id: Optional[str] = None,
    pipeline_config: Optional[Dict[str, Any]] = None,
    output_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> BaseAgent:
    """
    Create a planning agent with standard configuration.

    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        pipeline_config: Optional pipeline configuration for dynamic prompts
        output_callback: Optional callback for WebSocket output

    Returns:
        Configured planning agent
    """
    from ..prompts.planning_prompts import get_planning_prompt

    # Always use dynamic prompt generation
    prompt = get_planning_prompt(pipeline_config)

    return create_agent(
        name="planning-agent",
        system_prompt=prompt.strip(),
        tools=tools,
        project_id=project_id,
        output_callback=output_callback
    )


def create_coding_agent(
    tools: List[Any],
    project_id: Optional[str] = None,
    pipeline_config: Optional[Dict[str, Any]] = None,
    output_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> BaseAgent:
    """
    Create a coding agent with standard configuration.

    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        pipeline_config: Optional pipeline configuration for dynamic prompts
        output_callback: Optional callback for WebSocket output

    Returns:
        Configured coding agent
    """
    from ..prompts.coding_prompts import get_coding_prompt

    # Always use dynamic prompt generation
    prompt = get_coding_prompt(pipeline_config)

    return create_agent(
        name="coding-agent",
        system_prompt=prompt.strip(),
        tools=tools,
        project_id=project_id,
        output_callback=output_callback
    )


def create_testing_agent(
    tools: List[Any],
    project_id: Optional[str] = None,
    pipeline_config: Optional[Dict[str, Any]] = None,
    output_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> BaseAgent:
    """
    Create a testing agent with standard configuration.

    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        pipeline_config: Optional pipeline configuration for dynamic prompts
        output_callback: Optional callback for WebSocket output

    Returns:
        Configured testing agent
    """
    from ..prompts.testing_prompts import get_testing_prompt

    # Always use dynamic prompt generation
    prompt = get_testing_prompt(pipeline_config)

    return create_agent(
        name="testing-agent",
        system_prompt=prompt.strip(),
        tools=tools,
        project_id=project_id,
        output_callback=output_callback
    )


def create_review_agent(
    tools: List[Any],
    project_id: Optional[str] = None,
    pipeline_config: Optional[Dict[str, Any]] = None,
    output_callback: Optional[Callable[[str], Awaitable[None]]] = None
) -> BaseAgent:
    """
    Create a review agent with standard configuration.

    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        pipeline_config: Optional pipeline configuration for dynamic prompts
        output_callback: Optional callback for WebSocket output

    Returns:
        Configured review agent
    """
    from ..prompts.review_prompts import get_review_prompt

    # Always use dynamic prompt generation
    prompt = get_review_prompt(pipeline_config)

    return create_agent(
        name="review-agent",
        system_prompt=prompt.strip(),
        tools=tools,
        project_id=project_id,
        output_callback=output_callback
    )