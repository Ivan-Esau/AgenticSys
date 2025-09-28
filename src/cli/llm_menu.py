"""
LLM provider menu system.
"""

from typing import Optional, Dict, Any, List, Tuple
from src.core.llm.model_config_loader import get_model_config_loader
from .display import Display


def validate_provider_config(provider: str) -> tuple[bool, str]:
    """Validate provider configuration."""
    try:
        from src.core.llm.llm_providers import LLMProviderConfig
        api_key = LLMProviderConfig.get_api_key_for_provider(provider)
        if not api_key:
            return False, f"API key not configured for {provider}"
        return True, "Valid"
    except Exception as e:
        return False, str(e)


class LLMMenu:
    """Handles LLM provider selection menus."""

    def __init__(self):
        self.display = Display()
        self.loader = get_model_config_loader()

    def show_provider_menu(self) -> Optional[Dict[str, str]]:
        """Interactive menu for selecting LLM provider."""
        self.display.print_section("🤖 LLM PROVIDER CONFIGURATION")
        print("  Select your preferred Large Language Model provider:")
        print("  (Default provider from .env will be used if skipped)")
        print()

        # Load provider information from JSON configs
        available_providers = self.loader.get_available_providers()
        provider_summary = self.loader.get_provider_summary()

        print("🤖 AVAILABLE PROVIDERS:")
        provider_options = []

        option_num = 1
        for provider in available_providers:
            if provider in provider_summary:
                summary = provider_summary[provider]
                display_name = summary["display_name"]
                description = summary["description"]
                is_valid = summary["valid"]

                status_icon = "✅" if is_valid else "⚠️"
                provider_options.append((str(option_num), provider, display_name, description))
                print(f"  {option_num}. {display_name} - {description} {status_icon}")
                option_num += 1

        skip_option = str(option_num)
        provider_options.append((skip_option, "skip", "Skip", "Use current .env configuration"))
        print(f"  {skip_option}. Skip - Use current .env configuration ✅")

        print()
        # Show warnings for invalid providers
        invalid_providers = [p for p, s in provider_summary.items() if not s["valid"]]
        if invalid_providers:
            self.display.print_warning("Some providers missing API keys. Check your .env file.")

        max_option = len(provider_options)

        while True:
            provider_choice = input(f"\nSelect provider (1-{max_option}, or Enter to skip): ").strip()
            if provider_choice == "" or provider_choice == skip_option:
                self.display.print_success("Using default provider from .env")
                return None

            # Find selected provider
            selected_option = None
            for option_num, provider_id, display_name, description in provider_options:
                if provider_choice == option_num and provider_id != "skip":
                    selected_option = (provider_id, display_name)
                    break

            if not selected_option:
                self.display.print_error(f"Please select 1-{max_option} or press Enter to skip.")
                continue

            provider_id, display_name = selected_option

            # Validate provider configuration
            is_valid, message = validate_provider_config(provider_id)
            if not is_valid:
                self.display.print_error(message)
                print("Please configure the required API key in your .env file first.")
                continue

            self.display.print_success(f"Selected provider: {display_name}")

            # Optional model selection for the provider
            model = self.show_model_selection_menu(provider_id)

            return {
                "provider": provider_id,
                "model": model
            }

    def show_model_selection_menu(self, provider: str) -> Optional[str]:
        """Show model selection menu for the chosen provider."""
        models = self.loader.get_models_for_provider(provider)

        if not models:
            self.display.print_success(f"Using default model for {provider}")
            return None

        self.display.print_section(f"🎯 {provider.upper()} MODEL SELECTION")
        print("  Available models:")

        model_list = []
        for i, (model_id, model_info) in enumerate(models.items(), 1):
            display_name = model_info.get("display_name", model_id)
            description = model_info.get("description", "")
            context_length = model_info.get("context_length", "Unknown")

            print(f"  {i}. {display_name}")
            if description:
                print(f"      {description}")
            print(f"      Context: {context_length} tokens")

            # Show additional info for local models
            if "size_gb" in model_info:
                size_gb = model_info["size_gb"]
                print(f"      Size: {size_gb} GB")

            model_list.append((model_id, display_name))

        print(f"  {len(model_list) + 1}. Use provider default")

        while True:
            choice = input(f"\nSelect model (1-{len(model_list) + 1}): ").strip()

            if choice == str(len(model_list) + 1) or choice == "":
                self.display.print_success("Using provider default model")
                return None

            try:
                choice_int = int(choice)
                if 1 <= choice_int <= len(model_list):
                    selected_model_id = model_list[choice_int - 1][0]  # Get model_id
                    selected_display = model_list[choice_int - 1][1]  # Get display_name
                    self.display.print_success(f"Selected model: {selected_display}")
                    return selected_model_id
                else:
                    self.display.print_error(f"Please select 1-{len(model_list) + 1}.")
            except ValueError:
                self.display.print_error(f"Please enter a valid number (1-{len(model_list) + 1}).")