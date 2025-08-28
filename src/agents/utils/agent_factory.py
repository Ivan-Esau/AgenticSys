"""
Agent factory for standardized agent creation.
Provides consistent agent setup and configuration.
"""

from typing import List, Any, Optional
from ..base_agent import BaseAgent


def create_agent(
    name: str, 
    system_prompt: str, 
    tools: List[Any], 
    project_id: Optional[str] = None,
    model=None
) -> BaseAgent:
    """
    Create a standardized agent with consistent configuration.
    
    Args:
        name: Agent name (e.g., 'planning-agent')
        system_prompt: System prompt for the agent
        tools: List of tools available to the agent
        project_id: Optional project ID for state management
        model: Optional model override
        
    Returns:
        Configured BaseAgent instance
    """
    return BaseAgent(
        name=name,
        system_prompt=system_prompt,
        tools=tools,
        model=model,
        project_id=project_id
    )


def create_planning_agent(tools: List[Any], project_id: str = None) -> BaseAgent:
    """
    Create a planning agent with standard configuration.
    
    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        
    Returns:
        Configured planning agent
    """
    from ..prompts.planning_prompts import PLANNING_PROMPT
    
    return create_agent(
        name="planning-agent",
        system_prompt=PLANNING_PROMPT.strip(),
        tools=tools,
        project_id=project_id
    )


def create_coding_agent(tools: List[Any], project_id: str = None) -> BaseAgent:
    """
    Create a coding agent with standard configuration.
    
    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        
    Returns:
        Configured coding agent
    """
    from ..prompts.coding_prompts import CODING_PROMPT
    
    return create_agent(
        name="coding-agent",
        system_prompt=CODING_PROMPT.strip(),
        tools=tools,
        project_id=project_id
    )


def create_testing_agent(tools: List[Any], project_id: str = None) -> BaseAgent:
    """
    Create a testing agent with standard configuration.
    
    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        
    Returns:
        Configured testing agent
    """
    from ..prompts.testing_prompts import TESTING_PROMPT
    
    return create_agent(
        name="testing-agent",
        system_prompt=TESTING_PROMPT.strip(),
        tools=tools,
        project_id=project_id
    )


def create_review_agent(tools: List[Any], project_id: str = None) -> BaseAgent:
    """
    Create a review agent with standard configuration.
    
    Args:
        tools: Tools available to the agent
        project_id: Project ID for state management
        
    Returns:
        Configured review agent
    """
    from ..prompts.review_prompts import REVIEW_PROMPT
    
    return create_agent(
        name="review-agent",
        system_prompt=REVIEW_PROMPT.strip(),
        tools=tools,
        project_id=project_id
    )