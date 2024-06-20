import asyncio

from sqlalchemy import update
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from fortytwo.database import async_session
from fortytwo.database.models import User, Message
from fortytwo.manager import Manager
from fortytwo.providers.base import BaseProvider
from fortytwo.providers.openai import OpenAIProvider
from fortytwo.settings import Settings
from fortytwo.types import TelegramUser, TelegramMessage


class TelegramBot:
    def __init__(self, token: str = None):
        if not token:
            token = Settings.TELEGRAM_TOKEN
        self.token = token
        self.provider: BaseProvider = OpenAIProvider()
        self.manager = Manager()
        self.application = Application.builder().token(self.token).concurrent_updates(True).build()

        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('reset', self.reset))
        self.application.add_handler(CommandHandler('summarize', self.summarize))

    async def handle_text(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        telegram_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                                     title=tg_update.message.chat.title)
        manager = Manager()

        process_text_task = asyncio.ensure_future(manager.process_text(telegram_user, tg_update.message.text))
        await self.__send_typing_until_complete(tg_update, process_text_task)

        messages = await process_text_task

        await self.__send_messages(tg_update, messages)

    async def handle_image(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        photo_file = await tg_update.message.photo[-1].get_file()

        telegram_message = TelegramMessage(text=tg_update.message.caption, file=photo_file, media_group_id=tg_update.message.media_group_id)
        telegram_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                                     title=tg_update.message.chat.title)

        process_image_task = asyncio.ensure_future(self.manager.process_images(telegram_user, telegram_message))
        await self.__send_typing_until_complete(tg_update, process_image_task)

        messages = await process_image_task

        if messages:
            await self.__send_messages(tg_update, messages)

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
            sum_task = asyncio.ensure_future(self.manager.process_summarize(user.id, s))
            await self.__send_typing_until_complete(tg_update, sum_task)
            sum_results = await sum_task
            await tg_update.message.reply_text(sum_results, reply_to_message_id=tg_update.message.message_id)

    async def __send_messages(self, tg_update: Update, messages: list[str]):
        for message in messages:
            try:
                await tg_update.message.reply_text(message, reply_to_message_id=tg_update.message.message_id, parse_mode=ParseMode.MARKDOWN)
            except BadRequest as e:
                # If we received a BadRequest, it could be because the message contains a character that is not supported by markdown
                # In this case, we will send the message without markdown
                await tg_update.message.reply_text(message, reply_to_message_id=tg_update.message.message_id)

    async def __send_typing_until_complete(self, update: Update, task: asyncio.Task):
        while not task.done():
            await update.message.reply_chat_action('typing')
            await asyncio.sleep(2)

    def run(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
