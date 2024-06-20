import base64
from fortytwo.settings import Settings

import asyncio
import base64
import io

from sqlalchemy import select, update

from fortytwo.database import async_session
from fortytwo.database.models import User, Message, Picture
from fortytwo.providers.base import BaseProvider
from fortytwo.providers.openai import OpenAIProvider
from fortytwo.settings import Settings
from fortytwo.types import TelegramUser, TelegramMessage


class Manager:
    def __init__(self):
        self.provider: BaseProvider = OpenAIProvider()

    async def process_text(self, telegram_user: TelegramUser, telegram_message: str):
        async with async_session() as s:
            if not await self.__check_user_access(telegram_user):
                return ["You don't have access to a bot. Please contact the administrator.", ]
            user = await self.__get_or_create_user(telegram_user, s)

            chat_history = await self.__prepare_chat_history(user.id, s)

            message = Message(user_id=user.id, message_text=telegram_message)
            s.add(message)
            await s.commit()

            answer = await self.provider.text(telegram_message, chat_history=chat_history)

            message.answer = str(answer)
            message.total_tokens = answer.total_tokens
            message.completion_tokens = answer.completion_tokens
            message.prompt_tokens = answer.prompt_tokens

            await s.commit()

            ret_messages = [str(answer), ]

            if answer.total_tokens > Settings.MAX_TOTAL_TOKENS:
                sum_results = await self.process_summarize(user.id, s)
                ret_messages.append(f'*Your dialog was summorized:* \n\n{sum_results}')

            return ret_messages

    async def process_images(self, telegram_user: TelegramUser, telegram_message: TelegramMessage) -> list[str] | None:
        mm = io.BytesIO()
        await telegram_message.file.download_to_memory(out=mm)
        mm.seek(0)
        base64_image = base64.b64encode(mm.read()).decode('utf-8')

        async with async_session() as s:
            if not await self.__check_user_access(telegram_user):
                return ["You don't have access to a bot. Please contact the administrator.", ]
            user = await self.__get_or_create_user(telegram_user, s)

            pictures_base64 = []
            question = None
            chat_history = []

            if not telegram_message.media_group_id:
                question = telegram_message.text or "What is on the image?"
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
                        question = "What is on the images?"

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

            answer = await self.provider.image(pictures_base64, question=question, chat_history=chat_history)

            message.answer = str(answer)
            message.total_tokens = answer.total_tokens
            message.completion_tokens = answer.completion_tokens
            message.prompt_tokens = answer.prompt_tokens

            ret_messages = [str(answer), ]

            if answer.total_tokens > Settings.MAX_TOTAL_TOKENS:
                sum_results = await self.process_summarize(user.id, s)
                ret_messages.append(f'*Your dialog was summorized:* \n\n{sum_results}')

            return ret_messages

    async def __prepare_chat_history(self, user_id: int, session):
        messages = await Message.get_by_user(user_id, session)
        chat_history = []

        for message in messages:
            assistant_message = {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": message.answer or ''
                    },
                ]
            }

            user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message.message_text or ''
                    },
                ]
            }

            pictures = (await session.execute(select(Picture).where(Picture.message_id == message.id))).scalars().all()
            for picture in pictures:
                user_message['content'].append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{picture.file_base64}"
                        }
                    }
                )

            chat_history.append(user_message)
            chat_history.append(assistant_message)

        return chat_history

    async def __get_or_create_user(self, telegram_user: TelegramUser, s):
        user = await User.get_by_chat_id(telegram_user.id, s)

        if not user:
            user = User(chat_id=telegram_user.id, username=telegram_user.username, title=telegram_user.title)
            s.add(user)
            await s.commit()

        return user

    async def __check_user_access(self, telegram_user: TelegramUser):
        if not Settings.ALLOWED_USERS:
            return True

        allowed_users_list = Settings.ALLOWED_USERS.split(',')

        if telegram_user.username not in allowed_users_list and telegram_user.id not in allowed_users_list:
            return False

        return True

    async def process_summarize(self, user_id, s):
        chat_history = await self.__prepare_chat_history(user_id, s)
        system_prompt = "Summarize this dialog for me. Answer USING ONLY English not another language."

        summarized_dialog = await self.provider.text(question=system_prompt, system_prompt=system_prompt, chat_history=chat_history)
        await Message.clear_by_user(user_id, s)
        message = Message(user_id=user_id, message_text="What we've discussed earlier?", answer=str(summarized_dialog))
        s.add(message)
        await s.commit()

        return str(summarized_dialog)