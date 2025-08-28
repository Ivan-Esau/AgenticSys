"""
Agent prompts - clean separation of prompts from logic
"""

from .planning_prompts import PLANNING_PROMPT
from .coding_prompts import CODING_PROMPT
from .testing_prompts import TESTING_PROMPT
from .review_prompts import REVIEW_PROMPT

__all__ = ["PLANNING_PROMPT", "CODING_PROMPT", "TESTING_PROMPT", "REVIEW_PROMPT"]