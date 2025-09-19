from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from lexicon.lexicon import LEXICON_RU
from services.cache import get_rates
from keyboards.keyboards import create_rates_keyboard

rates_router = Router()

@rates_router.callback_query(F.data == 'exchange_rates')
async def process_rates_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    rates = await get_rates()

    def format_rate(currency_code):
        rate = rates.get(currency_code, 'N/A')
        if isinstance(rate, float):
            return f"{LEXICON_RU[currency_code.lower()]}: {rate:.2f} руб."
        return f"{LEXICON_RU[currency_code.lower()]}: {rate} руб."

    rates_text = f"{LEXICON_RU['rates_message']}\n"
    rates_text += f"{format_rate('EUR')}\n"
    rates_text += f"{format_rate('USD')}\n"
    rates_text += f"{format_rate('CNY')}\n"
    rates_text += f"{format_rate('KRW')}\n"

    await callback.message.answer(
        text=rates_text,
        reply_markup=create_rates_keyboard()
    )
    await callback.answer()
