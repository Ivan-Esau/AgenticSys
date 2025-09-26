"""
JSON-based model configuration loader and validator.
Allows users to easily add custom models and providers via JSON files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import importlib.util


class ModelConfigLoader:
    """Loads and validates model configurations from JSON files."""
    
    def __init__(self):
        # Path from src/core/llm/ to src/configs/models  
        self.config_dir = Path(__file__).parent.parent.parent / "configs" / "models"
        self._configs = {}
        self._loaded = False
    
    def load_all_configs(self) -> Dict[str, Dict]:
        """Load all provider configurations from JSON files."""
        if self._loaded:
            return self._configs
        
        self._configs = {}
        
        if not self.config_dir.exists():
            print(f"Warning: Model config directory not found: {self.config_dir}")
            return self._configs
        
        # Load all .json files (skip .template files)
        for config_file in self.config_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                provider_name = config.get("provider")
                if not provider_name:
                    print(f"Warning: Missing 'provider' field in {config_file}")
                    continue
                
                # Validate config structure
                if self._validate_config(config, config_file):
                    self._configs[provider_name] = config
                    print(f"Loaded model config: {provider_name} ({len(config.get('models', {}))} models)")
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON in {config_file}: {e}")
            except Exception as e:
                print(f"Error loading config {config_file}: {e}")
        
        self._loaded = True
        return self._configs
    
    def get_provider_config(self, provider: str) -> Optional[Dict]:
        """Get configuration for a specific provider."""
        configs = self.load_all_configs()
        return configs.get(provider)
    
    def get_available_providers(self) -> List[str]:
        """Get list of all available providers."""
        configs = self.load_all_configs()
        return list(configs.keys())
    
    def get_models_for_provider(self, provider: str) -> Dict[str, Dict]:
        """Get all models for a specific provider."""
        config = self.get_provider_config(provider)
        if config:
            return config.get("models", {})
        return {}
    
    def get_model_info(self, provider: str, model_id: str) -> Optional[Dict]:
        """Get detailed information about a specific model."""
        models = self.get_models_for_provider(provider)
        return models.get(model_id)
    
    def get_default_model(self, provider: str) -> Optional[str]:
        """Get the default model for a provider."""
        config = self.get_provider_config(provider)
        if config:
            return config.get("default_model")
        return None
    
    def get_task_model(self, provider: str, task_type: str) -> Optional[str]:
        """Get the recommended model for a specific task type."""
        config = self.get_provider_config(provider)
        if config:
            task_prefs = config.get("task_preferences", {})
            return task_prefs.get(task_type) or config.get("default_model")
        return None
    
    def validate_provider_setup(self, provider: str) -> Tuple[bool, str]:
        """Validate that a provider is properly configured."""
        config = self.get_provider_config(provider)
        if not config:
            return False, f"Provider '{provider}' not found in configurations"
        
        # Check if required package is available
        package_name = config.get("package_name")
        if package_name:
            try:
                importlib.import_module(package_name.replace("-", "_"))
            except ImportError:
                return False, f"Required package not installed: {package_name}"
        
        # Check API key requirement
        api_key_env = config.get("api_key_env")
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if not api_key:
                return False, f"Missing API key: {api_key_env} in environment variables"
        
        return True, "Valid configuration"
    
    def get_provider_summary(self) -> Dict[str, Dict]:
        """Get summary information for all providers."""
        configs = self.load_all_configs()
        summary = {}
        
        for provider, config in configs.items():
            is_valid, message = self.validate_provider_setup(provider)
            model_count = len(config.get("models", {}))
            
            summary[provider] = {
                "display_name": config.get("display_name", provider),
                "description": config.get("description", ""),
                "model_count": model_count,
                "valid": is_valid,
                "status_message": message,
                "requires_api_key": bool(config.get("api_key_env")),
                "default_model": config.get("default_model")
            }
        
        return summary
    
    def _validate_config(self, config: Dict, config_file: Path) -> bool:
        """Validate the structure of a configuration file."""
        required_fields = ["provider", "display_name", "models"]
        
        for field in required_fields:
            if field not in config:
                print(f"Warning: Missing required field '{field}' in {config_file}")
                return False
        
        # Validate models structure
        models = config.get("models", {})
        if not isinstance(models, dict):
            print(f"Warning: 'models' must be a dictionary in {config_file}")
            return False
        
        # Validate each model
        for model_id, model_info in models.items():
            if not isinstance(model_info, dict):
                print(f"Warning: Model '{model_id}' must be a dictionary in {config_file}")
                continue
            
            required_model_fields = ["id", "display_name", "description"]
            for field in required_model_fields:
                if field not in model_info:
                    print(f"Warning: Model '{model_id}' missing field '{field}' in {config_file}")
        
        return True
    
    def create_model_instance(self, provider: str, model_id: str = None, **kwargs) -> Any:
        """Create a model instance based on configuration."""
        config = self.get_provider_config(provider)
        if not config:
            raise ValueError(f"Provider '{provider}' not found")
        
        # Use default model if none specified
        if not model_id:
            model_id = config.get("default_model")
        
        if not model_id:
            raise ValueError(f"No model specified and no default for provider '{provider}'")
        
        # Get model info
        model_info = self.get_model_info(provider, model_id)
        if not model_info:
            raise ValueError(f"Model '{model_id}' not found for provider '{provider}'")
        
        # Get langchain class
        langchain_class = config.get("langchain_class")
        if not langchain_class:
            raise ValueError(f"No langchain_class specified for provider '{provider}'")
        
        # Import the class
        module_name, class_name = langchain_class.rsplit(".", 1)
        try:
            module = importlib.import_module(module_name)
            model_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Could not import {langchain_class}: {e}")
        
        # Prepare initialization parameters
        init_params = config.get("initialization_params", {}).copy()
        init_params.update(kwargs)
        
        # Set API key if required
        api_key_env = config.get("api_key_env")
        if api_key_env:
            api_key = os.getenv(api_key_env)
            if api_key:
                init_params["api_key"] = api_key
        
        # Set base URL if specified
        base_url_env = config.get("base_url_env")
        if base_url_env:
            base_url = os.getenv(base_url_env)
            if base_url:
                init_params["base_url"] = base_url
        elif config.get("default_base_url"):
            init_params["base_url"] = config["default_base_url"]
        
        # Set model ID
        init_params["model"] = model_info["id"]
        
        # Create and return model instance
        return model_class(**init_params)


# Global instance
_model_config_loader = ModelConfigLoader()


def get_model_config_loader() -> ModelConfigLoader:
    """Get the global model configuration loader instance."""
    return _model_config_loader