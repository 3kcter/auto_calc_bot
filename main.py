import asyncio
import logging

import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.config import Config, load_config
from handlers.common_handlers import common_router
from handlers.calculator_handlers import calculator_router
from handlers.url_handlers import url_router
from handlers.rates_handlers import rates_router
from handlers.admin_handlers import admin_router
from keyboards.set_menu import set_menu
from middlewares.subscription_middleware import SubscriptionMiddleware


async def main():
    config: Config = load_config()

    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(config=config)
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    await set_menu(bot)

    

    dp.include_router(admin_router)
    dp.include_router(common_router)
    dp.include_router(calculator_router)
    
    if os.getenv('ENABLE_PARSER', 'False').lower() == 'true':
        dp.include_router(url_router)
    
    dp.include_router(rates_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())