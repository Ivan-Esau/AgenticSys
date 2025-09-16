"""
Agent prompts - clean separation of prompts from logic
"""

from .planning_prompts import get_planning_prompt
from .coding_prompts import get_coding_prompt
from .testing_prompts import get_testing_prompt
from .review_prompts import get_review_prompt

__all__ = ["get_planning_prompt", "get_coding_prompt", "get_testing_prompt", "get_review_prompt"]