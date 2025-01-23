from abc import ABC, abstractmethod
from .types import AIResponse, UniversalChatHistory


class BaseProvider(ABC):
    provider_name: str = None

    @abstractmethod
    async def text(self, question: str, chat_history: UniversalChatHistory, system_prompt: str = None) -> AIResponse:
        pass

    @abstractmethod
    async def image(self, base64_images: list, question: str, chat_history: UniversalChatHistory, system_prompt: str = None) -> AIResponse:
        pass
    
    def is_image_supported(self) -> bool:
        return True
