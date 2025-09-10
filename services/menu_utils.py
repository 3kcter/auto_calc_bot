from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import create_main_menu_keyboard

async def send_start_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=LEXICON_RU['/start'],
        reply_markup=create_main_menu_keyboard()
    )