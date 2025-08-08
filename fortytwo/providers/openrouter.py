from .openai import OpenAIProvider
from fortytwo.settings import Settings


class OpenRouterProvider(OpenAIProvider):
    def __init__(self, api_key=Settings.OPENROUTER_API_KEY):
        super().__init__(api_key)
        self.model = Settings.OPENROUTER_MODEL
        self.base_api_url = "https://openrouter.ai/api/v1"
        self.provider_name = "OPENROUTER"

