import asyncio
from typing import Coroutine

from sqlalchemy import update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, constants
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import Application, CallbackContext, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from fortytwo.database import async_session
from fortytwo.database.models import Message, User
from fortytwo.logger import logger
from fortytwo.manager import Manager
from fortytwo.providers import available_providers
from fortytwo.providers.exceptions import ProviderError
from fortytwo.settings import Settings
from fortytwo.types import AIAnswer, TelegramMessage, TelegramUser

from .i18n import _


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

        try:
            coro = self.manager.process_text(telegram_user, tg_update.message.text)
            messages = await self.__execute_with_typing(coro, tg_update.message.chat.id)
            await self.__send_messages(tg_update, messages)
        except ProviderError as e:
            logger.error(f"{telegram_user.username} TEXT | ProviderError: {e}")
            await self.application.bot.send_message(tg_update.message.chat.id, _("Something went wrong with the AI provider during processing text. Please try again later."))

    async def handle_image(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        photo_file = await tg_update.message.photo[-1].get_file()

        telegram_message = TelegramMessage(text=tg_update.message.caption, file=photo_file, media_group_id=tg_update.message.media_group_id)
        telegram_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                                     title=tg_update.message.chat.title)

        try:
            coro = self.manager.process_images(telegram_user, telegram_message)
            messages = await self.__execute_with_typing(coro, tg_update.message.chat.id)
            await self.__send_messages(tg_update, messages)
        except ProviderError as e:
            await self.application.bot.send_message(tg_update.message.chat.id, _("Something went wrong with the AI provider during processing images. Please try again later."))
            logger.error(f"{telegram_user.username} IMAGE | ProviderError: {e}")
            return            

    async def __set_commands(self):
        await self.application.bot.set_my_commands([
            ('start', _('Start the bot')),
            ('reset', _('Reset the bot')),
            ('summarize', _('Summarize the dialog')),
            ('provider', _('Set the AI provider'))
        ])

    async def start(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                               title=tg_update.message.chat.title)
        await self.manager.get_user(tg_user)

        await self.__set_commands()
        await tg_update.message.reply_text(_('Hello!\n\n'
                                             'Send me a message and I will try to help you.\n'
                                             'You can also send me images.\n\n'
                                             'To change to AI Provider use /provider command\n'
                                             'To clear your dialog history use /reset command'))

    async def reset(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        tg_user = TelegramUser(id=tg_update.message.chat.id, username=tg_update.message.chat.username,
                               title=tg_update.message.chat.title)
        await self.manager.get_user(tg_user)

        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            await Message.clear_by_user(user.id, s)
        await tg_update.message.reply_text(_('Your dialog history has been cleared.'))

    async def __get_inline_keyboard_ask_another_ai_list(self, message_id) -> InlineKeyboardMarkup:
        keyboard = []
        message_provider = await self.manager.get_message_provider(message_id)

        for provider in available_providers():
            if provider != message_provider:
                keyboard.append([InlineKeyboardButton(provider, callback_data="another_" + provider + "_" + str(message_id))])

        reply_markup = InlineKeyboardMarkup(keyboard)

        return reply_markup

    async def handle_inline_keyboard(self, tg_update: Update, context: CallbackContext) -> None:
        query = tg_update.callback_query

        await query.answer(_("Processing..."))

        if query.data.startswith("set_provider_"):
            provider = query.data.split("_")[2]
            async with async_session() as s:
                user = await User.get_by_chat_id(query.message.chat.id, s)
                await user.set_provider(provider, s)
                await s.commit()
            await query.edit_message_text(_("Your current provider is *{provider}* \n").format(provider=provider), parse_mode=ParseMode.MARKDOWN)
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
                print(123)
                coro = self.manager.ask_another_provider(message_id, provider_name)
                print(456)
                answer = await self.__execute_with_typing(coro, query.message.chat.id)
                answer_text = _("Answer from *{provider_name}*:\n\n{answer}").format(provider_name=provider_name, answer=answer.answer)

                await self.__send_message(query.message.chat.id, answer_text, query.message.message_id)

        return None

    def __get_inline_keyboard_ask_another_ai(self, message_id: int) -> InlineKeyboardMarkup:
        keyboard = []

        if len(available_providers()) > 1:
            keyboard = ([InlineKeyboardButton(_('Ask another AI'), callback_data=f"another_{message_id}")], )

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
        await tg_update.message.reply_text(_('Your current provider is *{provider}* \nSelect new provider')
                                           .format(provider=user_data['provider']), reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def summarize(self, tg_update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with async_session() as s:
            user = await User.get_by_chat_id(tg_update.message.chat.id, s)
            coro = self.manager.process_summarize(user.id, s)
            sum_results = await self.__execute_with_typing(coro, tg_update.message.chat.id)
            await tg_update.message.reply_text(sum_results, reply_to_message_id=tg_update.message.message_id)

    async def __send_message(self, chat_id: int, message: str, reply_to: int = None, reply_markup: InlineKeyboardMarkup = None):
        """
        Send a message to the user.

        @param chat_id: Chat ID in Telegram
        @param message: Message text
        @param reply_to: Message ID to reply to
        @param reply_markup: InlineKeyboardMarkup
        """
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
        """
        Send a message to the user without checking the length.
        User only by __send_message method. Should not be used directly to avoid sending messages longer than allowed by Telegram.

        @param chat_id: Chat ID in Telegram
        @param message: Message text
        @param reply_to: Message ID to reply to
        @param reply_markup: InlineKeyboardMarkup
        """
        try:
            await self.application.bot.send_message(chat_id=chat_id, text=message,
                                                    reply_to_message_id=reply_to, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        except BadRequest as e:
            # If we receive a BadRequest, it could be because the message contains a character that is not supported by Markdown.
            # In this case, we will send the message without Markdown.
            await self.application.bot.send_message(chat_id=chat_id, text=message, reply_to_message_id=reply_to, reply_markup=reply_markup)

    async def __send_messages(self, tg_update: Update, messages: list[AIAnswer]):
        """
        Send a list of AIAnswer to the user.

        @param tg_update: Telegram Update object
        @param messages: List of AIAnswer
        """
        for message in messages:
            reply_markup = None
            if message.message_id > 0:
                reply_markup = self.__get_inline_keyboard_ask_another_ai(message.message_id)

            await self.__send_message(tg_update.message.chat.id, message.answer, tg_update.message.message_id, reply_markup=reply_markup)
            
    async def __execute_with_typing(self, coro: Coroutine, chat_id: int) -> AIAnswer | list[AIAnswer] | bool:
        """
        Execute a coroutine and show typing until the coroutine is done or the timeout is reached.
        """
        async def show_typing():
            while True:
                await self.application.bot.send_chat_action(chat_id, 'typing')
                await asyncio.sleep(2)
        try:
            typing_task = asyncio.create_task(show_typing())
            result = await asyncio.wait_for(coro, timeout=60)
            typing_task.cancel()
            return result
        except asyncio.TimeoutError:
            typing_task.cancel()
            await self.application.bot.send_message(chat_id, _("The operation took too long and was canceled."))
            return False
        except Exception as e:
            typing_task.cancel()
            raise e

    def run(self):
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
