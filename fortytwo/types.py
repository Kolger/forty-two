from dataclasses import dataclass
from telegram import File


@dataclass
class TelegramUser:
    id: int
    title: str
    username: str


@dataclass
class TelegramMessage:
    text: str
    file: File = None
    media_group_id: str = None


@dataclass
class AIAnswer:
    answer: str
    message_id: int
