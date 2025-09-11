from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import aiohttp
import asyncio
import datetime

from lexicon.lexicon import LEXICON_RU
from services.parser import parse_car_data, validate_and_normalize_url, parse_che168_selenium
from config.config import load_config, Config
from handlers.calculator_handlers import send_calculation_result, CalculatorFSM

url_router = Router()

def get_age_category_val(car_year: int) -> str:
    current_year = datetime.datetime.now().year
    age = current_year - car_year

    if age < 3:
        return "year_less_3"
    elif 3 <= age <= 5:
        return "year_3_5"
    else:
        return "year_more_5"

def get_age_category_display(age_val: str) -> str:
    if age_val == "year_less_3":
        return "младше 3"
    elif age_val == "year_3_5":
        return "3-5"
    else:
        return "старше 5"

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
        await message.answer(LEXICON_RU['processing_url'])
    processing_message = await message.answer(LEXICON_RU['processing_url'])

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
            await processing_message.delete() # Delete processing message
            return

        if error:
            await message.answer(f"Не удалось извлечь все необходимые данные со страницы: {error}. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            await processing_message.delete() # Delete processing message
            for admin_id in config.bot.admin_ids:
                await message.bot.send_message(admin_id, f"Ошибка парсинга URL: {url}")
{error}")
            return

        if car_data and all(car_data.get(k) is not None for k in ['year', 'cost', 'volume']):
            # Apply age categorization if year is available from parser
            if car_data.get('year') is not None:
                age_val = get_age_category_val(car_data['year'])
                car_data['year'] = age_val
                car_data['age_category'] = get_age_category_display(age_val)
            
            await state.update_data(**car_data)
            await send_calculation_result(message, state, config)
            await processing_message.delete() # Delete processing message
        else:
            await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            await processing_message.delete() # Delete processing message

    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке ссылки.")
        await processing_message.delete() # Delete processing message
        for admin_id in config.bot.admin_ids:
            await message.bot.send_message(admin_id, f"Произошла ошибка при обработке ссылки: {url}
{e}")

