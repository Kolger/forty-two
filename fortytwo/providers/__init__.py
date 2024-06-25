from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .base import BaseProvider
from fortytwo.settings import Settings

PROVIDERS = {
    "OPENAI": OpenAIProvider,
    "GEMINI": GeminiProvider
}


def get_provider(provider_name: str = None) -> BaseProvider:
    if provider_name is None:
        provider_name = Settings.PROVIDER

    if provider_name not in PROVIDERS:
        raise ValueError(f"Invalid provider: {Settings.PROVIDER}")

    return PROVIDERS[provider_name]()


def available_providers() -> list[str]:
    available_providers_list = []

    for provider_name in PROVIDERS:
        if getattr(Settings, f'{provider_name}_API_KEY'):
            available_providers_list.append(provider_name)

    return available_providers_list
