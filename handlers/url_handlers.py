from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import aiohttp

from lexicon.lexicon import LEXICON_RU
from services.parser import parse_car_data, validate_and_normalize_url
from config.config import load_config
from handlers.calculator_handlers import send_calculation_result, CalculatorFSM

url_router = Router()

@url_router.callback_query(F.data == 'calculate_by_url')
async def process_calculate_by_url_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(text=LEXICON_RU['enter_url'])
    await state.set_state(CalculatorFSM.url)
    await callback.answer()

@url_router.message(StateFilter(CalculatorFSM.url), F.text)
async def process_url_sent(message: Message, state: FSMContext):
    url, error = validate_and_normalize_url(message.text)
    if error:
        await message.answer(error)
        return

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html_content = await response.text()
                    car_data, error = parse_car_data(url, html_content)

                    if error:
                        await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
                        admin_ids = load_config().bot.admin_ids
                        for admin_id in admin_ids:
                            await message.bot.send_message(admin_id, f"Ошибка парсинга URL: {url}\n{error}")
                        return

                    if all(car_data.values()):
                        await state.update_data(**car_data)
                        await send_calculation_result(message, state)
                    else:
                        await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
                else:
                    await message.answer("Не удалось загрузить страницу. Пожалуйста, проверьте ссылку и попробуйте еще раз.")
                    admin_ids = load_config().bot.admin_ids
                    for admin_id in admin_ids:
                        await message.bot.send_message(admin_id, f"Ошибка загрузки страницы: {url}\nСтатус: {response.status}")
    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке ссылки.")
        admin_ids = load_config().bot.admin_ids
        for admin_id in admin_ids:
            await message.bot.send_message(admin_id, f"Произошла ошибка при обработке ссылки: {url}\n{e}")
