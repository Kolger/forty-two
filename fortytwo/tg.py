from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import base64
from fortytwo.settings import Settings

import os
import io
import asyncio
from fortytwo.providers.openai import OpenAIProvider
from fortytwo.providers.base import BaseProvider
from telegram.constants import ParseMode

from fortytwo.database.models import User, Message, Picture
from fortytwo.database import async_session
from sqlalchemy import select, func, update
from fortytwo.user import summarize
from fortytwo.providers.types import UserSchema, AssistantSchema, SystemSchema, ChatMessageSchema


class TelegramBot:
    def __init__(self, token: str = None):
        if not token:
            token = Settings.TELEGRAM_TOKEN
        self.token = token
        self.provider: BaseProvider = OpenAIProvider()
        self.application = Application.builder().token(self.token).concurrent_updates(True).build()
        #self.application = Application.builder().token(get_setting('TELEGRAM_TOKEN')).concurrent_updates(True).build()

        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('reset', self.reset))
        self.application.add_handler(CommandHandler('summarize', self.summarize))


    async def handle_text(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        async with async_session() as s:
            # user = (await s.execute(select(User).where(User.chat_id == update.message.chat.id))).scalar()
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            print(user)
            if not user:
                user = User(chat_id=tg_update.message.chat.id, username=tg_update.message.chat.username, title=tg_update.message.chat.title)
                s.add(user)
                await s.commit()

            # get latest messages
            # messages = (await s.execute(select(Message).where(Message.user == user.id))).scalars().all()
            #messages = await Message.get_by_user(user.id, s)
            #print(messages)
            chat_history = await self.__prepare_chat_history(user.id, s)

            #for message in messages:
            #    chat_history.append(UserSchema(content=message.message_text or '', role="user"))
            #    chat_history.append(AssistantSchema(content=message.answer or '', role="assistant"))

            message = Message(user_id=user.id, message_text=tg_update.message.text)
            s.add(message)
            await s.commit()

            asnwer_task = asyncio.ensure_future(self.provider.text(tg_update.message.text, chat_history=chat_history))
            await self.__send_typing_until_complete(tg_update, asnwer_task)

            answer = await asnwer_task

            message.answer = str(answer)
            message.total_tokens = answer.total_tokens
            message.completion_tokens = answer.completion_tokens
            message.prompt_tokens = answer.prompt_tokens

            await s.commit()

            await tg_update.message.reply_text(str(answer), reply_to_message_id=tg_update.message.message_id, parse_mode=ParseMode.MARKDOWN)

            if answer.total_tokens > Settings.MAX_TOTAL_TOKENS:
                sum = await self.__summarize(user.id, s)
                await tg_update.message.reply_text("summarize...", reply_to_message_id=tg_update.message.message_id)
                await tg_update.message.reply_text(sum, reply_to_message_id=tg_update.message.message_id)
            # sum = await summarize(user.id, s)
            # await update.message.reply_text(sum, reply_to_message_id=update.message.message_id)

    async def handle_image(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        photo_file = await tg_update.message.photo[-1].get_file()

        mm = io.BytesIO()
        await photo_file.download_to_memory(out=mm)
        mm.seek(0)
        base64_image = base64.b64encode(mm.read()).decode('utf-8')

        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)

            if not user:
                user = User(chat_id=tg_update.message.chat.id, username=tg_update.message.chat.username, title=tg_update.message.chat.title)
                s.add(user)
                await s.commit()

            pictures_base64 = []
            question = None
            chat_history = []

            if not tg_update.message.media_group_id:
                question = tg_update.message.caption
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
                    media_group_id=int(tg_update.message.media_group_id),
                    caption=tg_update.message.caption)

                s.add(picture)
                await s.commit()

                pictures_count_before = await Picture.count_by_media_group_id(int(tg_update.message.media_group_id), s)

                await asyncio.sleep(3)

                pictures_count_after = await Picture.count_by_media_group_id(int(tg_update.message.media_group_id), s)

                if pictures_count_before == pictures_count_after:
                    # it was the latest image, so send to AI
                    pictures = (await s.execute(select(Picture).where(Picture.media_group_id == int(tg_update.message.media_group_id)))).scalars().all()
                    chat_history = await self.__prepare_chat_history(user.id, s)

                    for picture in pictures:
                        pictures_base64.append(picture.file_base64)
                        if picture.caption:
                            question = picture.caption

                    message = Message(user_id=user.id, message_text=question)
                    s.add(message)
                    await s.commit()

                    await s.execute(
                        update(Picture)
                        .where(Picture.media_group_id == int(tg_update.message.media_group_id))
                        .values(message_id=message.id)
                    )
                    await s.commit()
                else:
                    return None
            image_task = asyncio.ensure_future(self.provider.image(pictures_base64, question=question, chat_history=chat_history))
            await self.__send_typing_until_complete(tg_update, image_task)
            answer = await image_task

            message.answer = str(answer)
            message.total_tokens = answer.total_tokens
            message.completion_tokens = answer.completion_tokens
            message.prompt_tokens = answer.prompt_tokens

            await s.commit()
            await tg_update.message.reply_text(str(answer), reply_to_message_id=tg_update.message.message_id, parse_mode=ParseMode.MARKDOWN)

            if answer.total_tokens > Settings.MAX_TOTAL_TOKENS:
                sum = await self.__summarize(user.id, s)
                await tg_update.message.reply_text("summarize...", reply_to_message_id=tg_update.message.message_id)
                await tg_update.message.reply_text(sum, reply_to_message_id=tg_update.message.message_id)

    async def __send_typing_until_complete(self, update: Update, task: asyncio.Task):
        while not task.done():
            await update.message.reply_chat_action('typing')
            await asyncio.sleep(2)

    async def __prepare_chat_history(self, user_id: int, session):
        messages = await Message.get_by_user(user_id, session)
        chat_history = []

        for message in messages:
            #chat_history.append(AssistantSchema(content=message.answer or '', role="assistant"))

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
                print("11111", picture)
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

    async def __summarize(self, user_id, s):
        chat_history = await self.__prepare_chat_history(user_id, s)
        # chat_history = [{"role": "user", "content": str(chat_history)}]
        system_prompt = "Summarize this dialog for me. Answer USING ONLY English not another language."

        summarized_dialog = await self.provider.text(question=system_prompt, system_prompt=system_prompt, chat_history=chat_history)
        await Message.clear_by_user(user_id, s)
        message = Message(user_id=user_id, message_text="What we've discussed earlier?", answer=str(summarized_dialog))
        s.add(message)
        await s.commit()

        return str(summarized_dialog)


    def run(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def start(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.application.bot.set_my_commands([
            ('start', 'Start the bot'),
            ('reset', 'Reset the bot'),
            ('summarize', 'Summarize the dialog')
        ])
        await tg_update.message.reply_text('Hi!')

    async def reset(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            await Message.clear_by_user(user.id, s)
        await tg_update.message.reply_text('RESETED')

    async def summarize(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            sum = await self.__summarize(user.id, s)
            await tg_update.message.reply_text(sum, reply_to_message_id=tg_update.message.message_id)