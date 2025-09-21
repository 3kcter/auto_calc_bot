from aiogram import Bot
from aiogram.types import BotCommand
from aiogram.methods import SetMyCommands
from aiogram.types import BotCommandScopeAllPrivateChats, BotCommandScopeChat

from lexicon.lexicon import LEXICON_COMMANDS_RU

async def set_menu(bot: Bot, admin_ids: list[int]):
    # Commands for regular users (excluding /admin)
    default_commands = [
        BotCommand(command=command,
            description=description)
        for command, description in LEXICON_COMMANDS_RU.items()
        if command != '/admin'
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeAllPrivateChats())

    # Commands for admin users (including /admin)
    admin_commands = [
        BotCommand(command=command,
            description=description)
        for command, description in LEXICON_COMMANDS_RU.items()
    ]
    for admin_id in admin_ids:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))