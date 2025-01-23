from .openai import OpenAIProvider
from fortytwo.settings import Settings


class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key=Settings.DEEPSEEK_API_KEY):
        super().__init__(api_key)
        self.model = Settings.DEEPSEEK_MODEL
        self.base_api_url = "https://api.deepseek.com"
        self.provider_name = "DEEPSEEK"
