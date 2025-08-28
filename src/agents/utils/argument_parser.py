"""
Common argument parsing for agents.
Provides standardized CLI argument handling across all agents.
"""

import argparse
from typing import Dict, Any


def create_agent_parser(agent_name: str, description: str = None) -> argparse.ArgumentParser:
    """
    Create a standardized argument parser for agents.
    
    Args:
        agent_name: Name of the agent (for help text)
        description: Optional description for the parser
        
    Returns:
        Configured ArgumentParser instance
    """
    if description is None:
        description = f"{agent_name.title()} Agent"
    
    parser = argparse.ArgumentParser(description=description)
    
    # Common arguments for all agents
    parser.add_argument(
        "--project-id", 
        required=True, 
        help="GitLab project ID"
    )
    parser.add_argument(
        "--no-tokens", 
        action="store_true", 
        help="Disable token streaming output"
    )
    
    return parser


def add_planning_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add planning-specific arguments to parser.
    
    Args:
        parser: ArgumentParser to modify
        
    Returns:
        Modified parser
    """
    parser.add_argument(
        "--apply", 
        action="store_true", 
        help="Apply changes (create branches and files)"
    )
    parser.add_argument(
        "--branch-hint", 
        default=None, 
        help="Hint for branch naming"
    )
    
    return parser


def add_coding_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add coding-specific arguments to parser.
    
    Args:
        parser: ArgumentParser to modify
        
    Returns:
        Modified parser
    """
    parser.add_argument(
        "--work-branch", 
        required=True, 
        help="Branch to work on"
    )
    parser.add_argument(
        "--issues", 
        nargs="*", 
        default=[], 
        help="Issues to implement"
    )
    parser.add_argument(
        "--fix-mode", 
        action="store_true", 
        help="Run in pipeline fix mode"
    )
    parser.add_argument(
        "--error-context", 
        default="", 
        help="Error context for fix mode"
    )
    
    return parser


def add_testing_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add testing-specific arguments to parser.
    
    Args:
        parser: ArgumentParser to modify
        
    Returns:
        Modified parser
    """
    parser.add_argument(
        "--work-branch", 
        required=True, 
        help="Branch to test"
    )
    parser.add_argument(
        "--fix-mode", 
        action="store_true", 
        help="Run in pipeline fix mode"
    )
    parser.add_argument(
        "--error-context", 
        default="", 
        help="Error context for fix mode"
    )
    
    return parser


def add_review_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    Add review-specific arguments to parser.
    
    Args:
        parser: ArgumentParser to modify
        
    Returns:
        Modified parser
    """
    parser.add_argument(
        "--work-branch", 
        required=True, 
        help="Branch to review and merge"
    )
    
    return parser


def parse_common_args(args) -> Dict[str, Any]:
    """
    Extract common arguments into a dictionary.
    
    Args:
        args: Parsed arguments from ArgumentParser
        
    Returns:
        Dictionary of common arguments
    """
    return {
        "project_id": args.project_id,
        "show_tokens": not args.no_tokens
    }