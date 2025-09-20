import os
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import create_main_menu_keyboard

async def send_start_menu(message: Message, state: FSMContext):
    await state.clear()
    photo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'photo_2025-09-10_16-14-39.jpg')
    photo = FSInputFile(photo_path)
    await message.answer_photo(
        photo=photo,
        caption=LEXICON_RU['/start'],
        reply_markup=create_main_menu_keyboard()
    )