from typing import Literal, Required, TypedDict, Union


class UserSchema(TypedDict):
    content: str
    role: Literal["user"]


class AssistantSchema(TypedDict):
    content: str
    role: Literal["assistant"]


class SystemSchema(TypedDict):
    content: str
    role: Literal["system"]


class AIResponse:
    content: str
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int

    def __init__(self, content: str, completion_tokens: int, prompt_tokens: int, total_tokens: int):
        self.content = content
        self.completion_tokens = completion_tokens
        self.prompt_tokens = prompt_tokens
        self.total_tokens = total_tokens

    def __str__(self):
        return self.content


ChatMessageSchema = UserSchema | AssistantSchema | SystemSchema
