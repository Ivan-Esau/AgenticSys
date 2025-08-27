"""
LLM (Large Language Model) configuration module.
Handles model initialization and configuration for DeepSeek and other LLMs.
"""

from langchain_deepseek.chat_models import ChatDeepSeek
from .config import Config
from typing import Optional


def make_model(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_retries: Optional[int] = None
) -> ChatDeepSeek:
    """
    Create and configure a DeepSeek chat model.
    
    Args:
        model: Model name (defaults to config)
        temperature: Temperature setting (defaults to config)
        max_retries: Maximum retry attempts (defaults to config)
        
    Returns:
        Configured ChatDeepSeek instance
    """
    # Use provided values or fall back to config
    model = model or Config.LLM_MODEL
    temperature = temperature if temperature is not None else Config.LLM_TEMPERATURE
    max_retries = max_retries or Config.LLM_MAX_RETRIES
    
    # Create model with streaming support
    return ChatDeepSeek(
        model=model,
        temperature=temperature,
        stream_usage=Config.LLM_STREAM_USAGE,
        max_retries=max_retries,
        api_key=Config.DEEPSEEK_API_KEY,
        base_url=Config.DEEPSEEK_BASE_URL
    )


def get_default_model() -> ChatDeepSeek:
    """
    Get a default configured model instance.
    
    Returns:
        Default ChatDeepSeek instance
    """
    return make_model()


class ModelConfig:
    """Model configuration constants and settings."""
    
    # Supported models
    DEEPSEEK_CHAT = "deepseek-chat"
    DEEPSEEK_CODER = "deepseek-coder"
    
    # Temperature presets
    TEMP_DETERMINISTIC = 0.0  # For consistent, deterministic outputs
    TEMP_FOCUSED = 0.3        # For focused, less creative outputs
    TEMP_BALANCED = 0.7       # For balanced creativity
    TEMP_CREATIVE = 1.0       # For maximum creativity
    
    # Token limits (approximate)
    MAX_CONTEXT_TOKENS = 32000
    MAX_OUTPUT_TOKENS = 4000
    
    @classmethod
    def get_model_for_task(cls, task_type: str) -> ChatDeepSeek:
        """
        Get a model configured for a specific task type.
        
        Args:
            task_type: Type of task ('coding', 'planning', 'review', etc.)
            
        Returns:
            Configured model for the task
        """
        task_configs = {
            'coding': {
                'model': cls.DEEPSEEK_CODER,
                'temperature': cls.TEMP_DETERMINISTIC
            },
            'planning': {
                'model': cls.DEEPSEEK_CHAT,
                'temperature': cls.TEMP_FOCUSED
            },
            'review': {
                'model': cls.DEEPSEEK_CHAT,
                'temperature': cls.TEMP_FOCUSED
            },
            'testing': {
                'model': cls.DEEPSEEK_CODER,
                'temperature': cls.TEMP_DETERMINISTIC
            },
            'pipeline': {
                'model': cls.DEEPSEEK_CHAT,
                'temperature': cls.TEMP_DETERMINISTIC
            },
            'creative': {
                'model': cls.DEEPSEEK_CHAT,
                'temperature': cls.TEMP_CREATIVE
            }
        }
        
        config = task_configs.get(task_type, {})
        return make_model(
            model=config.get('model'),
            temperature=config.get('temperature')
        )