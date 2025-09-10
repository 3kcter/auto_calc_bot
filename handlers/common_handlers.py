from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import create_main_menu_keyboard

common_router = Router()

async def send_start_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=LEXICON_RU['/start'],
        reply_markup=create_main_menu_keyboard()
    )

@common_router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    await send_start_menu(message, state)

@common_router.callback_query(lambda c: c.data == 'exit')
async def process_exit_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(text=LEXICON_RU['exit_message'])
    await send_start_menu(callback.message, state)
    await callback.answer()
