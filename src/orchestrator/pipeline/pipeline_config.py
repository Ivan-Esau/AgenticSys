"""
Simplified Pipeline Configuration - Stores tech stack information only.
Users provide their own .gitlab-ci.yml pipelines.
"""

from typing import Dict, Optional, Any


class PipelineConfig:
    """
    Simplified pipeline configuration - stores tech stack only.
    No pipeline generation - users provide their own .gitlab-ci.yml.
    """

    def __init__(self, tech_stack: Optional[Dict[str, str]] = None, mode: str = 'minimal'):
        """
        Initialize pipeline configuration with tech stack information.

        Args:
            tech_stack: Dict with 'backend', 'frontend', 'min_coverage', etc.
            mode: Unused - kept for backward compatibility
        """
        self.tech_stack = tech_stack or {}
        self.backend = self.tech_stack.get('backend', 'python')
        self.frontend = self.tech_stack.get('frontend', 'none')
        self.min_coverage = self.tech_stack.get('min_coverage', 70)

        # Create config dict with tech_stack for agents
        self.config = {
            'tech_stack': self.tech_stack,
            'backend': self.backend,
            'frontend': self.frontend,
            'min_coverage': self.min_coverage
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return self.config
