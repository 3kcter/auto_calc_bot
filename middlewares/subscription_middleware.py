import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import create_channel_keyboard
from config.config import Config


class SubscriptionMiddleware(BaseMiddleware):
    def __init__(self, config: Config):
        self.config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get('event_from_user')
        
        if user and user.id not in self.config.bot.admin_ids:
            bot = data['bot']
            try:
                chat_member = await bot.get_chat_member(
                    chat_id=self.config.bot.channel_id, user_id=user.id
                )
            except TelegramBadRequest as e:
                logging.error(f"TelegramBadRequest when checking subscription for user {user.id} in channel {self.config.bot.channel_id}: {e}")
                if isinstance(event, Message):
                    await event.answer("Произошла ошибка при проверке подписки. Пожалуйста, убедитесь, что бот добавлен в канал как администратор и имеет необходимые права. Попробуйте позже.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Произошла ошибка при проверке подписки. Пожалуйста, убедитесь, что бот добавлен в канал как администратор и имеет необходимые права. Попробуйте позже.")
                return
            except Exception as e:
                logging.error(f"Unexpected error when checking subscription for user {user.id} in channel {self.config.bot.channel_id}: {e}")
                if isinstance(event, Message):
                    await event.answer("Произошла непредвиденная ошибка при проверке подписки. Пожалуйста, попробуйте позже.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("Произошла непредвиденная ошибка при проверке подписки. Пожалуйста, попробуйте позже.")
                return

            if chat_member.status not in ['member', 'administrator', 'creator']:
                if isinstance(event, Message):
                    await event.answer(
                        text=LEXICON_RU['subscription_required'],
                        reply_markup=create_channel_keyboard(self.config)
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer()
                    await event.message.answer(
                        text=LEXICON_RU['subscription_required'],
                        reply_markup=create_channel_keyboard(self.config)
                    )
                return
        
        return await handler(event, data)
