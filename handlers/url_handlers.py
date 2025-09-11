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
from keyboards.keyboards import create_kazan_question_keyboard, create_kazan_question_url_keyboard

url_router = Router()

def get_age_category(car_year: int) -> str:
    current_year = datetime.datetime.now().year
    age = current_year - car_year

    if age < 3:
        return "младше 3"
    elif 3 <= age <= 5:
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
            return

        if error:
            await processing_message.delete() # Delete processing message on error
            await message.answer(f"Не удалось извлечь все необходимые данные со страницы: {error}. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            for admin_id in config.bot.admin_ids:
                await message.bot.send_message(admin_id, f"Ошибка парсинга URL: {url}\n{error}")
            return

        if car_data and all(car_data.get(k) is not None for k in ['year', 'cost', 'volume']):
            # Apply age categorization if year is available from parser
            if car_data.get('year') is not None:
                car_data['age_category'] = get_age_category(car_data['year'])
            
            await state.update_data(**car_data)

            # Check for Kazan question if country is China or Korea
            if car_data.get('country') in ['china', 'korea']:
                await processing_message.edit_text(
                    text=LEXICON_RU['is_from_kazan_question'],
                    reply_markup=create_kazan_question_url_keyboard()
                )
                await state.update_data(prompt_message_id=processing_message.message_id)
                await state.set_state(CalculatorFSM.is_from_kazan)
                return # Exit after setting state for Kazan question
            else:
                await processing_message.delete() # Delete processing message before sending result
                await send_calculation_result(message, state, config)
                await state.clear() # Clear the state for non-Kazan countries
                return # Exit after sending result
        else:
            await processing_message.delete() # Delete processing message on missing data
            await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            return # Exit after sending error message

    except Exception as e:
        await processing_message.delete() # Delete processing message on unexpected error
        await message.answer(f"Произошла ошибка при обработке ссылки.")
        for admin_id in config.bot.admin_ids:
            await message.bot.send_message(admin_id, f"Произошла ошибка при обработке ссылки: {url}\n{e}")
        return # Exit after sending error message


