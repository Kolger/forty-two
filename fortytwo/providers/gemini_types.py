from typing import Literal, TypedDict, Union, NotRequired, List


class GeminiInlineData(TypedDict):
    mime_type: Literal["image/jpeg"]
    data: str


class GeminiUserMessage(TypedDict):
    parts: List
    role: Literal["user"]
    inline_data: NotRequired[GeminiInlineData]


class GeminiAssistantMessage(TypedDict):
    parts: List
    role: Literal["model"]


GeminiChatHistory = List[Union[GeminiUserMessage, GeminiAssistantMessage]]


class GeminiPayload(TypedDict):
    system_instruction: dict
    contents: GeminiChatHistory
