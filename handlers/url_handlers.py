from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
import aiohttp
import datetime

from lexicon.lexicon import LEXICON_RU
from services.parser import parse_encar_requests, validate_and_normalize_url, parse_che168_requests
from config.config import load_config, Config
from handlers.calculator_handlers import send_calculation_result, CalculatorFSM
from keyboards.keyboards import create_kazan_question_keyboard, create_kazan_question_url_keyboard

url_router = Router()

def get_age_category_val(car_year: int, car_month: int = 1) -> str:
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    
    age_in_months = (current_year - car_year) * 12 + (current_month - car_month)
    
    if age_in_months < 36:
        return "year_less_3"
    elif 36 <= age_in_months <= 60:
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

    processing_message = await message.answer(LEXICON_RU['processing_url'])

    try:
        car_data = None
        error = None

        if 'encar.com' in url:
            car_data, error = await parse_encar_requests(url)
        elif 'che168.com' in url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        car_data, error = parse_che168_requests(html_content)
                    else:
                        error = f"Failed to load page, status: {response.status}"
        else:
            await message.answer("Пожалуйста, отправьте ссылку на сайт che168.com или encar.com")
            await processing_message.delete()
            return

        if car_data and car_data.get('special_message'):
            await message.answer(car_data['special_message'])
            await processing_message.delete()
            await state.clear()
            return

        if error:
            await message.answer(f"Не удалось извлечь все необходимые данные со страницы: {error}. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            await processing_message.delete()
            for admin_id in config.bot.admin_ids:
                await message.bot.send_message(admin_id, f"Ошибка парсинга URL: {url}\n{error}")
            return

        if car_data and (car_data.get('engine_type') == 'electro' or (car_data.get('power') and not car_data.get('volume'))):
            await message.answer("Для расчёта электромобиля обратитесь, пожалуйста, к менеджеру - @makauto_manager")
            await processing_message.delete()
            await state.clear()
            return

        if car_data and car_data.get('year') is not None and car_data.get('cost') is not None:
            if car_data.get('volume') is None:
                 await message.answer("Не удалось извлечь объем двигателя. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
                 await processing_message.delete()
                 return

            if car_data.get('year') is not None:
                car_data['original_year'] = car_data['year'] 
                age_val = get_age_category_val(car_data['year'], car_data.get('month', 1))
                car_data['year'] = age_val 
                car_data['age_category'] = get_age_category_display(age_val)
            
            await state.update_data(**car_data)

            sent_message = await message.answer(
                text=LEXICON_RU['is_from_kazan_question'],
                reply_markup=create_kazan_question_url_keyboard()
            )
            await state.update_data(prompt_message_id=sent_message.message_id)
            await state.set_state(CalculatorFSM.is_from_kazan)

            await processing_message.delete()
        else:
            await message.answer("Не удалось извлечь все необходимые данные со страницы. Пожалуйста, попробуйте другую ссылку или воспользуйтесь обычным калькулятором.")
            await processing_message.delete()

    except Exception as e:
        await message.answer(f"Произошла ошибка при обработке ссылки.")
        await processing_message.delete()
        for admin_id in config.bot.admin_ids:
            await message.bot.send_message(admin_id, f"Произошла ошибка при обработке ссылки: {url}\n{e}")
