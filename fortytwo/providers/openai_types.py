from typing import Literal, TypedDict, Union


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
