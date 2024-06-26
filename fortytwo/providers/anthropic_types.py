from typing import Literal, Required, TypedDict, Union, NotRequired, List
from dataclasses import dataclass
from enum import Enum
from .types import RequestHeaders

AnthropicRequestHeaders = TypedDict('AnthropicRequestHeaders', {
    'Content-Type': Literal["application/json"],
    'x-api-key': str,
    'anthropic-version': str
})
