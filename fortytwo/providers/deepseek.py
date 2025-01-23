from .openai import OpenAIProvider
from fortytwo.settings import Settings
from .base import BaseProvider
from .exceptions import ProviderError
from .openai_types import OpenAIAssistantMessage, OpenAIChatMessage, OpenAIImageMessage, OpenAIPayload, OpenAIUserMessage
from .types import AIResponse, RequestHeaders, UniversalChatHistory

class DeepSeekProvider(OpenAIProvider):
    def __init__(self, api_key=Settings.DEEPSEEK_API_KEY):
        super().__init__(api_key)
        self.model = Settings.DEEPSEEK_MODEL
        self.base_api_url = "https://api.deepseek.com"
        self.provider_name = "DEEPSEEK"

    def _convert_chat_history(self, chat_history: UniversalChatHistory) -> list[OpenAIChatMessage]:
        converted_chat_history = []

        for message in chat_history:
            if message['role'] == "user":
                user_message: OpenAIUserMessage = {
                    "role": "user",
                    "content": message['content']['text']
                }

                converted_chat_history.append(user_message)

            elif message['role'] == "assistant":
                assistant_message: OpenAIAssistantMessage = {
                    "role": "assistant",
                    "content": message['content']['text']
                }

                converted_chat_history.append(assistant_message)

        return converted_chat_history
    
    def _prepare_payload(self, text, base64_images=(), chat_history: list = (),
                          system_prompt: str = None) -> OpenAIPayload:
        if not system_prompt:
            system_prompt = self.default_system_prompt

        payload: OpenAIPayload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                *self._convert_chat_history(chat_history),
                {
                    "role": "user",
                    "content":text
                }
            ],
            "max_tokens": Settings.MAX_COMPLETION_TOKENS
        }

        return payload
    
    def is_image_supported(self) -> bool:
        return False