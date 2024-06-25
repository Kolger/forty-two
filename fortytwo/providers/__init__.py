from .openai import OpenAIProvider
from .gemini import GeminiProvider
from .base import BaseProvider
from fortytwo.settings import Settings

PROVIDERS = {
    "OPENAI": OpenAIProvider,
    "GEMINI": GeminiProvider
}


def get_provider(provider_name = None) -> BaseProvider:
    if provider_name is None:
        provider_name = Settings.PROVIDER

    if provider_name not in PROVIDERS:
        raise ValueError(f"Invalid provider: {Settings.PROVIDER}")

    return PROVIDERS[provider_name]()
