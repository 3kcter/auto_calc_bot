from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import create_main_menu_keyboard
from handlers.calculator_handlers import CalculatorFSM
from services.menu_utils import send_start_menu

common_router = Router()

@common_router.message(CommandStart())
async def process_start_command(message: Message, state: FSMContext):
    await send_start_menu(message, state)

@common_router.callback_query(lambda c: c.data == 'exit')
async def process_exit_press(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state != CalculatorFSM.result:
        await callback.message.delete()
    await send_start_menu(callback.message, state)
    await callback.answer()
