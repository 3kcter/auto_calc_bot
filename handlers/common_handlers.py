from aiogram import Router, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatMemberStatus
from aiogram import F

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import create_channel_keyboard, create_restart_keyboard
from handlers.calculator_handlers import CalculatorFSM
from services.menu_utils import send_start_menu
from config.config import Config

common_router = Router()

@common_router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext, bot: Bot, config: Config):
    user_id = message.from_user.id
    is_admin = user_id in config.bot.admin_ids
    is_member = False
    if not is_admin:
        member = await bot.get_chat_member(chat_id=config.bot.channel_id, user_id=user_id)
        is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]

    if is_admin or is_member:
        await send_start_menu(message, state)
    else:
        await message.answer(
            text=LEXICON_RU['subscription_required'],
            reply_markup=create_channel_keyboard(config)
        )

@common_router.callback_query(lambda c: c.data == 'exit')
async def process_exit_press(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != CalculatorFSM.result:
        await callback.message.delete()
    await send_start_menu(callback.message, state)
    await callback.answer()

@common_router.callback_query(F.data == '/start')
async def process_start_callback(callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config):
    user_id = callback.from_user.id
    is_admin = user_id in config.bot.admin_ids
    is_member = False
    if not is_admin:
        member = await bot.get_chat_member(chat_id=config.bot.channel_id, user_id=user_id)
        is_member = member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]

    if is_admin or is_member:
        await send_start_menu(callback.message, state)
    else:
        await callback.message.answer(
            text=LEXICON_RU['subscription_required'],
            reply_markup=create_channel_keyboard(config)
        )
    await callback.answer()

@common_router.callback_query(F.data == 'restart_calculation')
async def process_restart_calculation(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text="Выберите способ расчета:",
        reply_markup=create_restart_keyboard()
    )
    await callback.answer()