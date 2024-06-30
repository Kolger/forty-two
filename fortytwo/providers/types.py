from typing import Literal, Required, TypedDict, Union, NotRequired, List
from dataclasses import dataclass
from enum import Enum


RequestHeaders = TypedDict('RequestHeaders', {
    'Content-Type': Literal["application/json"],
    'Authorization': NotRequired[str],
})


@dataclass
class AIResponse:
    class Status(Enum):
        OK = "OK"
        ERROR = "ERROR"

    content: str
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    provider: str
    # enum ok / error
    status: Status = Status.OK

    def __str__(self):
        return self.content


class UniversalChatContent(TypedDict):
    text: str
    images: NotRequired[List[str]]


class UniversalChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: UniversalChatContent


UniversalChatHistory = List[UniversalChatMessage]
