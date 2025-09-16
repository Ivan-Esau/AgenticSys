"""
Multi-provider LLM configuration module with JSON-based configuration.
Supports dynamic loading of providers and models from JSON files.
"""

from typing import Optional, Any, List
from src.core.llm.config import Config
from src.core.llm.model_config_loader import get_model_config_loader
import os


class Providers:
    """Dynamic provider class that loads from JSON configurations."""
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all available providers from JSON configs."""
        loader = get_model_config_loader()
        return loader.get_available_providers()
    
    @classmethod
    def get_default(cls) -> str:
        """Get the default provider."""
        return os.getenv("LLM_PROVIDER", "deepseek").lower()


class ModelConfigs:
    """Dynamic model configurations loaded from JSON files."""
    
    @classmethod
    def get_models_for_provider(cls, provider: str) -> dict:
        """Get all models for a specific provider."""
        loader = get_model_config_loader()
        models = loader.get_models_for_provider(provider)
        return {model_id: model_info.get("display_name", model_id) 
                for model_id, model_info in models.items()}
    
    


class LLMProviderConfig:
    """Configuration class for LLM providers using JSON configs."""
    
    # Current provider (from env or default)
    PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()
    
    @classmethod
    def get_api_key_for_provider(cls, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        loader = get_model_config_loader()
        config = loader.get_provider_config(provider)
        if not config:
            return None
        
        api_key_env = config.get("api_key_env")
        if api_key_env:
            return os.getenv(api_key_env, "")
        return None
    
    @classmethod
    def get_base_url_for_provider(cls, provider: str) -> Optional[str]:
        """Get base URL for a specific provider."""
        loader = get_model_config_loader()
        config = loader.get_provider_config(provider)
        if not config:
            return None
        
        base_url_env = config.get("base_url_env")
        if base_url_env:
            base_url = os.getenv(base_url_env)
            if base_url:
                return base_url
        
        return config.get("default_base_url")
    
    @classmethod
    def get_default_model_for_provider(cls, provider: str) -> Optional[str]:
        """Get default model for a specific provider."""
        loader = get_model_config_loader()
        return loader.get_default_model(provider)


def create_model(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    **kwargs
) -> Any:
    """
    Create a model instance for the specified provider using JSON configurations.
    
    Args:
        provider: LLM provider name (loaded from JSON configs)
        model: Specific model name (optional, uses provider default)
        temperature: Temperature setting (optional, uses config default)
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Configured model instance for the provider
        
    Raises:
        ValueError: If provider is not supported
        ImportError: If required provider package is not installed
    """
    loader = get_model_config_loader()
    provider = (provider or LLMProviderConfig.PROVIDER).lower()
    
    # Check if provider exists in configs
    if provider not in loader.get_available_providers():
        available = ", ".join(loader.get_available_providers())
        raise ValueError(f"Unsupported provider: {provider}. Available: {available}")
    
    # Override temperature if provided
    if temperature is not None:
        kwargs["temperature"] = temperature
    elif "temperature" not in kwargs:
        kwargs["temperature"] = Config.LLM_TEMPERATURE
    
    # Add max_retries if not specified
    if "max_retries" not in kwargs:
        kwargs["max_retries"] = Config.LLM_MAX_RETRIES
    
    # Create model instance using the loader
    return loader.create_model_instance(provider, model, **kwargs)


def get_default_model():
    """Get the default configured model based on current provider settings."""
    return create_model()


def get_model_for_task(task_type: str):
    """
    Get a model configured for a specific task type using JSON configurations.
    
    Args:
        task_type: Type of task ('coding', 'planning', 'review', etc.)
        
    Returns:
        Configured model optimized for the task
    """
    loader = get_model_config_loader()
    provider = LLMProviderConfig.PROVIDER
    
    # Get task-specific model from JSON config
    task_model = loader.get_task_model(provider, task_type)
    
    # Task-specific temperature settings
    task_temperatures = {
        'coding': 0.0,      # Deterministic for code generation
        'testing': 0.0,     # Deterministic for test generation  
        'planning': 0.3,    # Slightly creative for planning
        'review': 0.3,      # Focused for code review
        'creative': 1.0,    # Maximum creativity
    }
    
    temperature = task_temperatures.get(task_type, Config.LLM_TEMPERATURE)
    
    return create_model(
        provider=provider,
        model=task_model,
        temperature=temperature
    )


def validate_provider_config(provider: str) -> tuple[bool, str]:
    """
    Validate configuration for a specific provider using JSON configurations.
    
    Args:
        provider: Provider name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    loader = get_model_config_loader()
    return loader.validate_provider_setup(provider)


def get_provider_info():
    """Get information about current provider configuration."""
    loader = get_model_config_loader()
    provider = LLMProviderConfig.PROVIDER
    is_valid, message = validate_provider_config(provider)
    
    return {
        'provider': provider,
        'valid': is_valid,
        'message': message,
        'available_providers': loader.get_available_providers(),
        'summary': loader.get_provider_summary()
    }