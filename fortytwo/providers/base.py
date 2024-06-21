from abc import ABC, abstractmethod
from .types import OpenAIChatMessage, AIResponse


class BaseProvider(ABC):
    @abstractmethod
    async def text(self, question: str, chat_history: list[OpenAIChatMessage], system_prompt: str = None) -> AIResponse:
        pass

    @abstractmethod
    async def image(self, base64_images: list, question: str, chat_history: list[OpenAIChatMessage], system_prompt: str = None) -> AIResponse:
        pass
