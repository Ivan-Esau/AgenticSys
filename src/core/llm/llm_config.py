"""
LLM (Large Language Model) configuration module.
Handles model initialization and configuration for multiple providers.
"""

from src.core.llm.llm_providers import create_model, get_model_for_task
from typing import Optional, Any


def make_model(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: Optional[int] = None,
    provider: Optional[str] = None
) -> Any:
    """
    Create and configure a chat model.
    
    Args:
        model: Model name (defaults to provider default)
        temperature: Temperature setting (defaults to config)
        max_retries: Maximum retry attempts (defaults to config)
        provider: LLM provider (deepseek, openai, claude, etc.)
        
    Returns:
        Configured model instance for the specified provider
    """
    return create_model(
        provider=provider,
        model=model,
        temperature=temperature,
        max_retries=max_retries
    )


class ModelConfig:
    """Model configuration constants and settings."""
    
    # Temperature presets
    TEMP_DETERMINISTIC = 0.0  # For consistent, deterministic outputs
    TEMP_FOCUSED = 0.3        # For focused, less creative outputs
    TEMP_BALANCED = 0.7       # For balanced creativity
    TEMP_CREATIVE = 1.0       # For maximum creativity
    
    # Token limits (approximate - varies by provider)
    MAX_CONTEXT_TOKENS = 32000
    MAX_OUTPUT_TOKENS = 4000
    
    @classmethod
    def get_model_for_task(cls, task_type: str) -> Any:
        """
        Get a model configured for a specific task type.
        Uses the new multi-provider system.
        
        Args:
            task_type: Type of task ('coding', 'planning', 'review', etc.)
            
        Returns:
            Configured model for the task
        """
        return get_model_for_task(task_type)