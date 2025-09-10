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
    eur_rate = rates.get('EUR', 'N/A')
    usd_rate = rates.get('USD', 'N/A')
    krw_rate = rates.get('KRW', 'N/A')
    cny_rate = rates.get('CNY', 'N/A')

    if isinstance(eur_rate, float):
        eur_rate = f'{eur_rate:.2f}'
    if isinstance(usd_rate, float):
        usd_rate = f'{usd_rate:.2f}'
    if isinstance(krw_rate, float):
        krw_rate = f'{krw_rate:.2f}'
    if isinstance(cny_rate, float):
        cny_rate = f'{cny_rate:.2f}'

    rates_text = f"{LEXICON_RU['rates_message']}\n"
    
    # Display EUR
    eur_rate = rates.get('EUR', 'N/A')
    if isinstance(eur_rate, float):
        rates_text += f"{LEXICON_RU['eur']}: {eur_rate:.2f} руб.\n"
    else:
        rates_text += f"{LEXICON_RU['eur']}: {eur_rate} руб.\n"

    # Display USD
    usd_rate = rates.get('USD', 'N/A')
    if isinstance(usd_rate, float):
        rates_text += f"{LEXICON_RU['usd']}: {usd_rate:.2f} руб.\n"
    else:
        rates_text += f"{LEXICON_RU['usd']}: {usd_rate} руб.\n"

    # Display CNY
    cny_rate = rates.get('CNY', 'N/A')
    if isinstance(cny_rate, float):
        rates_text += f"{LEXICON_RU['cny']}: {cny_rate:.2f} руб.\n"
    else:
        rates_text += f"{LEXICON_RU['cny']}: {cny_rate} руб.\n"

    # Display KRW
    krw_rate = rates.get('KRW', 'N/A')
    if isinstance(krw_rate, float):
        rates_text += f"{LEXICON_RU['krw']}: {krw_rate:.2f} руб.\n"
    else:
        rates_text += f"{LEXICON_RU['krw']}: {krw_rate} руб.\n"

    await callback.message.answer(
        text=rates_text,
        reply_markup=create_rates_keyboard()
    )
    await callback.answer()
