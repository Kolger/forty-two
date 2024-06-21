from typing import Literal, Required, TypedDict, Union
from dataclasses import dataclass


class OpenAITextContent(TypedDict):
    type: Literal["text", "image_url"]
    text: str


class OpenAIImageContent(TypedDict):
    url: str


class OpenAIImageMessage(TypedDict):
    type: Literal["image_url"]
    image_url: OpenAIImageContent


class OpenAIUserMessage(TypedDict):
    content: list[OpenAITextContent | OpenAIImageMessage]
    role: Literal["user"]


class OpenAIAssistantMessage(TypedDict):
    content: list[OpenAITextContent]
    role: Literal["assistant"]


class OpenAISystemMessage(TypedDict):
    content: str
    role: Literal["system"]


OpenAIChatMessage = Union[OpenAIUserMessage, OpenAIAssistantMessage, OpenAISystemMessage]


class OpenAIPayload(TypedDict):
    model: str
    messages: list[OpenAIChatMessage]
    max_tokens: int


OpenAIHeaders = TypedDict('OpenAIHeaders', {
    'Content-Type': Literal["application/json"],
    'Authorization': str
})


@dataclass
class AIResponse:
    content: str
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

    def __str__(self):
        return self.content



