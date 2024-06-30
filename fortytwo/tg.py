import asyncio

from sqlalchemy import update
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler, CallbackContext

from fortytwo.database import async_session
from fortytwo.database.models import User, Message
from fortytwo.manager import Manager
from fortytwo.providers import available_providers
from fortytwo.settings import Settings
from fortytwo.types import TelegramUser, TelegramMessage, AIAnswer


class TelegramBot:
    def __init__(self, token: str = None):
        if not token:
            token = Settings.TELEGRAM_TOKEN
        self.token = token
        self.manager = Manager()
        self.application = Application.builder().token(self.token).concurrent_updates(True).build()

        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_image))
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('reset', self.reset))
        self.application.add_handler(CommandHandler('provider', self.provider))
        self.application.add_handler(CommandHandler('summarize', self.summarize))
        self.application.add_handler(CallbackQueryHandler(self.handle_inline_keyboard))

    async def handle_text(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        telegram_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                                     title=tg_update.message.chat.title)

        process_text_task = asyncio.ensure_future(self.manager.process_text(telegram_user, tg_update.message.text))
        await self.__send_typing_until_complete(tg_update.message.chat.id, process_text_task)

        messages = await process_text_task

        await self.__send_messages(tg_update, messages)

    async def handle_image(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        photo_file = await tg_update.message.photo[-1].get_file()

        telegram_message = TelegramMessage(text=tg_update.message.caption, file=photo_file, media_group_id=tg_update.message.media_group_id)
        telegram_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                                     title=tg_update.message.chat.title)

        process_image_task = asyncio.ensure_future(self.manager.process_images(telegram_user, telegram_message))
        await self.__send_typing_until_complete(tg_update.message.chat.id, process_image_task)

        messages = await process_image_task

        if messages:
            await self.__send_messages(tg_update, messages)

    async def __set_commands(self):
        await self.application.bot.set_my_commands([
            ('start', 'Start the bot'),
            ('reset', 'Reset the bot'),
            ('summarize', 'Summarize the dialog'),
            ('provider', 'Set the AI provider')
        ])

    async def start(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                               title=tg_update.message.chat.title)
        await self.manager.get_user(tg_user)

        await self.__set_commands()
        await tg_update.message.reply_text('Hi!')

    async def reset(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                               title=tg_update.message.chat.title)
        await self.manager.get_user(tg_user)

        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            await Message.clear_by_user(user.id, s)
        await tg_update.message.reply_text('Your dialog history has been cleared.')

    async def __get_inline_keyboard_ask_another_ai_list(self, message_id) -> InlineKeyboardMarkup:
        keyboard = []
        message_provider = await self.manager.get_message_provider(message_id)

        for provider in available_providers():
            if provider != message_provider:
                keyboard.append([InlineKeyboardButton(provider, callback_data="another_" + provider + "_" + str(message_id))])

        reply_markup = InlineKeyboardMarkup(keyboard)

        return reply_markup

    async def handle_inline_keyboard(self, tg_update: Update, _: CallbackContext) -> None:
        query = tg_update.callback_query

        await query.answer("Processing...")

        if query.data.startswith("set_provider_"):
            provider = query.data.split("_")[2]
            async with async_session() as s:
                user = await User.get_by_chat_id(query.message.chat.id, s)
                await user.set_provider(provider, s)
                await s.commit()
            await query.edit_message_text(f"Your current provider is *{provider}* \n", parse_mode=ParseMode.MARKDOWN)
            return None

        if query.data.startswith("another_"):
            splitted_query = query.data.split("_")
            if len(splitted_query) == 2:
                message_id = query.data.split("_")[1]
                reply_markup = await self.__get_inline_keyboard_ask_another_ai_list(message_id)
                await query.edit_message_reply_markup(reply_markup)
            elif len(splitted_query) == 3:
                message_id = int(query.data.split("_")[2])
                provider_name = query.data.split("_")[1]
                keyboard = self.__get_inline_keyboard_ask_another_ai(message_id)
                await query.edit_message_reply_markup(keyboard)
                ask_another_provider_task = asyncio.ensure_future(self.manager.ask_another_provider(message_id, provider_name))
                await self.__send_typing_until_complete(query.message.chat.id, ask_another_provider_task)
                answer = await ask_another_provider_task
                answer_text = f"Answer from *{provider_name}*:\n\n{answer.answer}"

                await self.__send_message(query.message.chat.id, answer_text, query.message.message_id)

        return None

    def __get_inline_keyboard_ask_another_ai(self, message_id: int) -> InlineKeyboardMarkup:
        keyboard = ([InlineKeyboardButton('Ask another AI', callback_data=f"another_{message_id}")], )

        return InlineKeyboardMarkup(keyboard)

    async def provider(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = []

        for provider in available_providers():
            keyboard.append([InlineKeyboardButton(provider, callback_data="set_provider_" + provider)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await self.__set_commands()
        #user = await User.get_by_chat_id(tg_update.message.chat.id, s)
        tg_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                                                title=tg_update.message.chat.title)
        user_data = await self.manager.get_user(tg_user)
        await tg_update.message.reply_text(f'Your current provider is *{user_data['provider']}* \nSelect new provider', reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def summarize(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            sum_task = asyncio.ensure_future(self.manager.process_summarize(user.id, s))
            await self.__send_typing_until_complete(tg_update.message.chat.id, sum_task)
            sum_results = await sum_task
            await tg_update.message.reply_text(sum_results, reply_to_message_id=tg_update.message.message_id)

    async def __send_message(self, chat_id: int, message: str, reply_to: int = None, reply_markup: InlineKeyboardMarkup = None):
        await self.__set_commands()
        if len(message) < constants.MessageLimit.MAX_TEXT_LENGTH:
            await self.__send_message_raw(chat_id, message, reply_to, reply_markup)
        else:
            # message longer than limit allowed by telegram for 1 message
            # in this case we split answer from AI to multiple messages
            chunks = [message[i:i + constants.MessageLimit.MAX_TEXT_LENGTH] for i in
                      range(0, len(message), constants.MessageLimit.MAX_TEXT_LENGTH)]

            for i, chunk in enumerate(chunks):
                if i == len(chunks) - 1:
                    # last message in chunks, only for last message add reply_markup
                    await self.__send_message_raw(chat_id, chunk, reply_to, reply_markup)
                else:
                    await self.__send_message_raw(chat_id, chunk, reply_to)

    async def __send_message_raw(self, chat_id: int, message: str, reply_to: int = None, reply_markup: InlineKeyboardMarkup = None):
        try:
            await self.application.bot.send_message(chat_id=chat_id, text=message,
                                                    reply_to_message_id=reply_to, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest as e:
            # If we receive a BadRequest, it could be because the message contains a character that is not supported by Markdown.
            # In this case, we will send the message without Markdown.
            await self.application.bot.send_message(chat_id=chat_id, text=message, reply_to_message_id=reply_to, reply_markup=reply_markup)

    async def __send_messages(self, tg_update: Update, messages: list[AIAnswer]):
        for message in messages:
            reply_markup = None
            if message.message_id > 0:
                reply_markup = self.__get_inline_keyboard_ask_another_ai(message.message_id)

            await self.__send_message(tg_update.message.chat.id, message.answer, tg_update.message.message_id, reply_markup=reply_markup)

    async def __send_typing_until_complete(self, chat_id: int, task: asyncio.Task):
        try:
            await asyncio.wait_for(self.__send_typing_until_complete_infinite(chat_id, task), timeout=60)
        except asyncio.TimeoutError:
            task.cancel()
            await self.application.bot.send_message(chat_id, "The operation took too long and was canceled.")

    async def __send_typing_until_complete_infinite(self, chat_id: int, task: asyncio.Task):
        while not task.done():
            await self.application.bot.send_chat_action(chat_id, 'typing')
            await asyncio.sleep(2)

    def run(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
