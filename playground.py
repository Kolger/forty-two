import asyncio
import base64
import io
import json

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from fortytwo.database import async_session
from fortytwo.database.models import User, Message, Picture
from fortytwo.logger import logger
from fortytwo.providers import get_provider
from fortytwo.providers.base import BaseProvider
from fortytwo.providers.openai import OpenAIProvider
from fortytwo.providers.gemini import GeminiProvider
from fortytwo.providers.types import UniversalChatMessage, UniversalChatContent, UniversalChatHistory, AIResponse
from fortytwo.settings import Settings
from fortytwo.types import TelegramUser, TelegramMessage, AIAnswer
from datetime import datetime, timedelta, timezone


async def main():
    ...


if __name__ == '__main__':
    asyncio.run(main())
