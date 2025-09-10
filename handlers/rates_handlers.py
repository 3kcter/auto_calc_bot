from aiogram import Router, F
from aiogram.types import CallbackQuery

from lexicon.lexicon import LEXICON_RU
from services.cache import get_rates

rates_router = Router()

@rates_router.callback_query(F.data == 'exchange_rates')
async def process_rates_press(callback: CallbackQuery):
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

    await callback.message.answer(
        text=f"{LEXICON_RU['rates_message']}\n"
                f"{LEXICON_RU['eur']}: {eur_rate} руб.\n"
                f"{LEXICON_RU['usd']}: {usd_rate} руб.\n"
                f"{LEXICON_RU['krw']}: {krw_rate} руб.\n"
                f"{LEXICON_RU['cny']}: {cny_rate} руб."
    )
    await callback.answer()
