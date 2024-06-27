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


class Manager:
    def __init__(self):
        #self.provider: BaseProvider = OpenAIProvider()
        #self.provider: BaseProvider = GeminiProvider()
        #self.provider: BaseProvider = get_provider()
        ...

    async def get_message_provider(self, message_id: int):
        """
        Get provider name for a message
        This method is used in Telegram class for inline buttons

        :param message_id: Message ID
        """

        async with async_session() as s:
            message = (await s.execute(select(Message).where(message_id == Message.id))).scalar()
            return message.provider

    async def process_text(self, telegram_user: TelegramUser, telegram_message: str) -> list[AIAnswer]:
        async with async_session() as s:
            if not await self.__check_user_access(telegram_user):
                return [AIAnswer(answer="You don't have access to a bot. Please contact the administrator.", message_id=-1), ]
            user = await self.__get_or_create_user(telegram_user, s)

            chat_history = await self.__prepare_chat_history(user.id, s)

            message = Message(user_id=user.id, message_text=telegram_message)
            s.add(message)
            await s.commit()

            answer = await self.__get_provider(user.provider).text(telegram_message, chat_history=chat_history)

            if answer.status == answer.Status.ERROR:
                message.is_error = True

            message.answer = str(answer)
            message.total_tokens = answer.total_tokens
            message.completion_tokens = answer.completion_tokens
            message.prompt_tokens = answer.prompt_tokens
            message.provider = answer.provider

            await s.commit()

            await self.__log_message(telegram_user, message, 'TEXT')

            ret_messages = [AIAnswer(answer=str(answer), message_id=message.id), ]

            if answer.total_tokens > Settings.MAX_TOTAL_TOKENS:
                sum_results = await self.process_summarize(user.id, s)
                ret_messages.append(dict(answer=f'*Your dialog was summorized:* \n\n{sum_results}', message_id=-1))

            return ret_messages

    async def process_images(self, telegram_user: TelegramUser, telegram_message: TelegramMessage) -> list[AIAnswer] | None:
        mm = io.BytesIO()
        await telegram_message.file.download_to_memory(out=mm)
        mm.seek(0)
        base64_image = base64.b64encode(mm.read()).decode('utf-8')

        async with async_session() as s:
            if not await self.__check_user_access(telegram_user):
                return [AIAnswer(answer="You don't have access to a bot. Please contact the administrator.", message_id=-1), ]
            user = await self.__get_or_create_user(telegram_user, s)

            pictures_base64 = []
            question = None
            chat_history = []

            if not telegram_message.media_group_id:
                question = telegram_message.text or ""
                chat_history = await self.__prepare_chat_history(user.id, s)
                message = Message(user_id=user.id, message_text=question)
                s.add(message)
                await s.commit()

                picture = Picture(
                    file_base64=base64_image,
                    caption=question,
                    message_id=message.id
                )
                s.add(picture)
                await s.commit()

                pictures_base64.append(base64_image)
            else:
                picture = Picture(
                    file_base64=base64_image,
                    media_group_id=int(telegram_message.media_group_id),
                    caption=telegram_message.text)

                s.add(picture)
                await s.commit()

                pictures_count_before = await Picture.count_by_media_group_id(int(telegram_message.media_group_id), s)

                await asyncio.sleep(3)

                pictures_count_after = await Picture.count_by_media_group_id(int(telegram_message.media_group_id), s)

                if pictures_count_before == pictures_count_after:
                    # it was the latest image, so send to AI
                    pictures = (await s.execute(select(Picture).where(int(telegram_message.media_group_id) == Picture.media_group_id))).scalars().all()
                    chat_history = await self.__prepare_chat_history(user.id, s)

                    for picture in pictures:
                        pictures_base64.append(picture.file_base64)
                        if picture.caption:
                            question = picture.caption

                    if question is None:
                        question = ""

                    message = Message(user_id=user.id, message_text=question)
                    s.add(message)
                    await s.commit()

                    await s.execute(
                        update(Picture)
                        .where(int(telegram_message.media_group_id) == Picture.media_group_id)
                        .values(message_id=message.id)
                    )
                    await s.commit()
                else:
                    return None

            answer = await self.__get_provider(user.provider).image(pictures_base64, question=question, chat_history=chat_history)

            if answer.status == answer.Status.ERROR:
                message.is_error = True

            message.answer = str(answer)
            message.total_tokens = answer.total_tokens
            message.completion_tokens = answer.completion_tokens
            message.prompt_tokens = answer.prompt_tokens
            message.provider = answer.provider

            await s.commit()

            ret_messages = [AIAnswer(answer=str(answer), message_id=message.id), ]

            await self.__log_message(telegram_user, message, 'IMAGE')

            if answer.total_tokens > Settings.MAX_TOTAL_TOKENS:
                sum_results = await self.process_summarize(user.id, s)
                ret_messages.append(dict(answer=f'*Your dialog was summorized:* \n\n{sum_results}', message_id=-1))

            return ret_messages

    async def __prepare_chat_history(self, user_id: int, session, until_message_id: int = None) -> UniversalChatHistory:
        if until_message_id:
            messages = await Message.get_by_user_until_id(user_id, session, until_message_id)
        else:
            messages = await Message.get_by_user(user_id, session)

        chat_history: UniversalChatHistory = list()

        for message in messages:
            assistant_message: UniversalChatContent = {"text": message.answer or ''}
            user_message: UniversalChatContent = {"text": message.message_text or '', 'images': []}
            pictures: list[Picture] = (await session.execute(select(Picture).where(Picture.message_id == message.id))).scalars().all()

            for picture in pictures:
                user_message['images'].append(picture.file_base64)

            chat_history.append(UniversalChatMessage(role='user', content=user_message))
            chat_history.append(UniversalChatMessage(role='assistant', content=assistant_message))

        return chat_history

    async def __get_or_create_user(self, telegram_user: TelegramUser, s):
        user = await User.get_by_chat_id(telegram_user.id, s)

        if not user:
            user = User(chat_id=telegram_user.id, username=telegram_user.username, title=telegram_user.title)
            s.add(user)
            await s.commit()

        return user

    async def get_user(self, telegram_user: TelegramUser):
        async with async_session() as s:
            user = await self.__get_or_create_user(telegram_user, s)

            return dict(
                user_id=user.id,
                provider=user.provider or Settings.PROVIDER
            )

    def __get_provider(self, user_provider: str | None) -> BaseProvider:
        if user_provider:
            selected_provider = user_provider
        else:
            selected_provider = Settings.PROVIDER

        return get_provider(selected_provider)

    async def __check_user_access(self, telegram_user: TelegramUser):
        if not Settings.ALLOWED_USERS:
            return True

        allowed_users_list = Settings.ALLOWED_USERS.split(',')

        if telegram_user.username not in allowed_users_list and telegram_user.id not in allowed_users_list:
            return False

        return True

    async def __log_message(self, telegram_user: TelegramUser, message: Message, prefix: str = 'TEXT'):
        if Settings.LOG_MESSAGES:
            logger.info(f"Q {prefix} | User: {telegram_user.username} {message.message_text.replace('\n', ' ').replace('\r', ' ')}")
            logger.info(f"A {prefix} | User: {telegram_user.username} "
                        f"{message.answer.replace('\n', ' ').replace('\r', ' ')} | "
                        f"Prompt tokens: {message.prompt_tokens}, "
                        f"Completion tokens: {message.completion_tokens}, "
                        f"Total tokens: {message.total_tokens}")

    async def process_summarize(self, user_id, s):
        chat_history = await self.__prepare_chat_history(user_id, s)
        system_prompt = "Summarize this dialog (what we'e discussed before) for me. Answer (this time) USING ONLY English not another language."

        user = (await s.execute(select(User).where(User.id == user_id))).scalar()

        summarized_dialog = await self.__get_provider(user.provider).text(question=system_prompt, system_prompt=system_prompt, chat_history=chat_history)
        await Message.clear_by_user(user_id, s)
        message = Message(user_id=user_id, message_text="What we've discussed earlier?", answer=str(summarized_dialog))
        s.add(message)
        await s.commit()

        return str(summarized_dialog)

    async def ask_another_provider(self, message_id: int, provider_name: str) -> AIAnswer:
        provider = get_provider(provider_name)

        async with async_session() as s:
            message = await s.get(Message, message_id, options=[selectinload(Message.user)])
            pictures: list[Picture] = (await s.execute(select(Picture).where(Picture.message_id == message.id))).scalars().all()
            chat_history = await self.__prepare_chat_history(user_id=message.user_id, session=s, until_message_id=message_id)

            if len(pictures) > 0:
                pictures_base64 = [picture.file_base64 for picture in pictures]
                answer = await provider.image(base64_images=pictures_base64, question=message.message_text, chat_history=chat_history)
            else:
                answer = await provider.text(message.message_text, chat_history=chat_history)

            new_message = Message(
                user_id=message.user.id,
                message_text=message.message_text,
                parent_message_id=message_id,
                answer=str(answer),
                provider=provider_name,
                is_ask_another_ai=True,
                completion_tokens=answer.completion_tokens,
                prompt_tokens=answer.prompt_tokens,
                total_tokens=answer.total_tokens)

            s.add(new_message)
            await s.commit()
            await self.__log_message(TelegramUser(id=message.user.chat_id, username=message.user.username, title=message.user.title),
                                     new_message, f'ASK ANOTHER ({provider_name})')

            return AIAnswer(answer=str(answer), message_id=message_id)