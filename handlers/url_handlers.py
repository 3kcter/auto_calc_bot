from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import aiohttp
import asyncio

from lexicon.lexicon import LEXICON_RU
from services.parser import parse_car_data, validate_and_normalize_url, parse_che168_selenium
from config.config import load_config, Config
from handlers.calculator_handlers import send_calculation_result, CalculatorFSM

url_router = Router()

@url_router.callback_query(F.data == 'calculate_by_url')
async def process_calculate_by_url_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(text=LEXICON_RU['enter_url'])
    await state.set_state(CalculatorFSM.url)
    await callback.answer()

@url_router.message(StateFilter(CalculatorFSM.url), F.text)
async def process_url_sent(message: Message, state: FSMContext, config: Config):
    url, error = validate_and_normalize_url(message.text)
    if error:
        await message.answer(error)
        return

    await message.answer(LEXICON_RU['processing_url'])

    try:
        if 'encar.com' in url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        car_data, error = parse_car_data(url, html_content)
                    else:
                        error = f"Failed to load page, status: {response.status}"
                        car_data = None
        elif 'che168.com' in url:
            car_data, error = await asyncio.to_thread(parse_che168_selenium, url)
        else:
            await message.answer("Пожалуйста, отправьте ссылку на сайт encar.com или che168.com")
            return

        if error:
            await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            for admin_id in config.bot.admin_ids:
                await message.bot.send_message(admin_id, f"Ошибка парсинга URL: {url}\n{error}")
            return

        if car_data and all(car_data.get(k) is not None for k in ['year', 'cost', 'volume']):
            await state.update_data(**car_data)
            await send_calculation_result(message, state, config)
        else:
            await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")

    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке ссылки.")
        for admin_id in config.bot.admin_ids:
            await message.bot.send_message(admin_id, f"Произошла ошибка при обработке ссылки: {url}\n{e}")