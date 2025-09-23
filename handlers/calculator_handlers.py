from aiogram import F, Router
import re
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import (
    create_year_keyboard, create_cost_keyboard, create_volume_keyboard,
    create_country_keyboard, create_after_calculation_keyboard,
    create_engine_type_keyboard, create_kazan_question_keyboard, create_hybrid_type_keyboard,
    create_restart_keyboard
)
from services.calculator import calculate_cost
from services.menu_utils import send_start_menu
from config.config import load_user_calc_config, Config

def format_number(n):
    return f"{n:,}".replace(",", " ")

calculator_router = Router()

class CalculatorFSM(StatesGroup):
    year = State()
    engine_type = State()
    hybrid_type = State()
    country = State()
    is_from_kazan = State()
    cost = State()
    volume = State()
    power = State()
    url = State()
    result = State()

COUNTRY_INFO = {
    'china': {'symbol': '¥', 'name': 'юанях'},
    'korea': {'symbol': '₩', 'name': 'вонах'}
}

def get_calculation_details(data, costs):
    currency_symbol = (COUNTRY_INFO.get(data['country'], {}).get('symbol', ''))

    params_lines = []
    if data.get('cost'):
        params_lines.append(f"💰 Стоимость: {format_number(data['cost'])} {currency_symbol}")
    
    display_month = data.get('month')
    year_str = str(data.get('original_year', data.get('year')))
    if display_month and isinstance(data.get('original_year'), int):
        year_str = f"{data.get('original_year')}-{display_month:02d}"
    params_lines.append(f"📅 Год выпуска: {(year_str)}")
    
    if data.get('volume', 0) > 0:
        params_lines.append(f"⚙️ Объём двигателя: {data['volume']} см³")
    
    if data.get('power'):
        power_unit = data.get('power_unit', 'кВт')
        power_display = str(data.get('power_display', data['power']))
        params_lines.append(f"⚡️ Мощность: {power_display} {power_unit}")

    params_section = "\n".join(params_lines)

    payments_lines = [
        f"🇷🇺 Таможенная пошлина: \n• {format_number(round(costs['customs_payments']))} руб.",
        f"📑 Таможенный сбор: \n• {format_number(round(costs['customs_clearance']))} руб.",
        f"♻️ Утилизационный сбор: \n• {format_number(costs['recycling_fee'])} руб."
    ]
    if costs.get('excise_tax', 0) > 0:
        payments_lines.insert(2, f"💸 Акциз: \n• {format_number(round(costs['excise_tax']))} руб.")
    if costs.get('vat', 0) > 0:
        payments_lines.append(f"📊 НДС: \n• {format_number(round(costs['vat']))} руб.")

    payments_section = "\n".join(payments_lines)

    total_cost_rub_formatted = format_number(round(costs['total_cost_rub']))

    return params_section, payments_section, total_cost_rub_formatted


async def send_calculation_result(message_or_callback, state: FSMContext, config: Config):
    data = await state.get_data()
    calc_config = await load_user_calc_config()
    
    costs = await calculate_cost(
        data.get('year'), 
        data['cost'], 
        data['country'], 
        data.get('volume', 0), 
        calc_config, 
        data['engine_type'], 
        data.get('is_from_kazan'), 
        data.get('power', 0)
    )

    params_section, payments_section, total_cost_rub_formatted = get_calculation_details(data, costs)
    
    output_text = (
        f"📋<b>Итоги расчёта для вашего авто</b>📋 \n\n"
        f"<b>Параметры:</b>\n\n{params_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Расчётные платежи:</b>\n\n{payments_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Итого:</b> <code>{total_cost_rub_formatted}</code> руб."
    )

    output_text += "\n\n⚠️ Курсы валют часто меняются, поэтому для уверенности советуем запросить актуальный расчёт у менеджера"

    if isinstance(message_or_callback, Message):
        target_message = message_or_callback
        user_id = target_message.from_user.id
    else: 
        target_message = message_or_callback.message
        user_id = message_or_callback.from_user.id

    is_admin = user_id in config.bot.admin_ids

    await target_message.answer(
        text=output_text,
        reply_markup=create_after_calculation_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )
    await state.set_state(CalculatorFSM.result)


@calculator_router.callback_query(F.data == 'detailed_calculation', StateFilter(CalculatorFSM.result))
async def process_detailed_calculation_press(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    calc_config = await load_user_calc_config()

    costs = await calculate_cost(
        data.get('year'),
        data['cost'],
        data['country'],
        data.get('volume', 0),
        calc_config,
        data['engine_type'],
        data.get('is_from_kazan'),
        data.get('power', 0)
    )

    params_section, main_payments_section, total_cost_rub_formatted = get_calculation_details(data, costs)

    additional_expenses_lines = []
    if data['country'] == 'korea':
        additional_expenses_lines.append(f"🇰🇷 Комиссия дилера: \n• {format_number(round(costs['dealer_commission']))} руб.")
        additional_expenses_lines.append(f"🚛 Транспорт по Корее: \n• {format_number(round(costs['korea_inland_transport']))} руб.")
        additional_expenses_lines.append(f"🚢 Погрузка и фрахт: \n• {format_number(round(costs['korea_port_transport_loading']))} руб.")
        additional_expenses_lines.append(f"🇷🇺 Расходы по Владивостоку: \n• {format_number(round(costs['vladivostok_expenses']))} руб.")
        additional_expenses_lines.append(f"🚚 Доставка до вашего города: \n• {format_number(round(costs['logistics_vladivostok_kazan']))} руб.")
        additional_expenses_lines.append(f"📎 Прочие расходы: \n• {format_number(round(costs['other_expenses']))} руб.")
    elif data['country'] == 'china':
        additional_expenses_lines.append(f"🇨🇳 Комиссия дилера: \n• {format_number(round(costs['dealer_commission']))} руб.")
        additional_expenses_lines.append(f"📦 Доставка до Казахстана и документы: \n• {format_number(round(costs['china_documents_delivery']))} руб.")
        additional_expenses_lines.append(f"🚚 Логистика: \n• {format_number(round(costs['logistics_cost']))} руб.")
        if costs.get('lab_svh_cost', 0) > 0:
            additional_expenses_lines.append(f"🔬 Лаборатория и СВХ: \n• {format_number(round(costs['lab_svh_cost']))} руб.")
        additional_expenses_lines.append(f"📎 Прочие расходы: \n• {format_number(round(costs['other_expenses']))} руб.")

    if costs.get('delivery_to_region_cost', 0) > 0:
        label = LEXICON_RU['lab_svh_not_kazan_rub']
        additional_expenses_lines.append(f"🔬 {label}: \n• {format_number(round(costs['delivery_to_region_cost']))} руб.")
    
    additional_expenses_section = "\n".join(additional_expenses_lines)
    country_name = "Корея" if data['country'] == 'korea' else "Китай"

    
    output_text = (
        f"📋<b>Детальный расчёт для вашего авто</b>📋\n\n"
        f"<b>Параметры:</b>\n\n{params_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Основные платежи:</b>\n\n{main_payments_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Дополнительные расходы ({country_name}):</b>\n\n{additional_expenses_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Итоговая стоимость:</b> <code>{total_cost_rub_formatted}</code> руб.")
    output_text += "\n\n⚠️ Курсы валют часто меняются, поэтому для уверенности советуем запросить актуальный расчёт у менеджера"
    await callback.message.answer(text=output_text, parse_mode="HTML")
    await callback.answer()



@calculator_router.callback_query(F.data == 'calculator')
async def process_calculator_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(
        text=LEXICON_RU['select_year'],
        reply_markup=create_year_keyboard()
    )
    await state.set_state(CalculatorFSM.year)
    await callback.answer()

@calculator_router.callback_query(F.data == 'back')
async def process_back_press(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

    if current_state == CalculatorFSM.year:
        await callback.message.edit_text(
            text="Выберите способ расчета:",
            reply_markup=create_restart_keyboard()
        )
        await state.clear()
    elif current_state == CalculatorFSM.engine_type:
        await callback.message.edit_text(text=LEXICON_RU['select_year'], reply_markup=create_year_keyboard())
        await state.set_state(CalculatorFSM.year)
    elif current_state == CalculatorFSM.url:
        await callback.message.edit_text(
            text="Выберите способ расчета:",
            reply_markup=create_restart_keyboard()
        )
        await state.clear()
    elif current_state == CalculatorFSM.hybrid_type:
        await callback.message.edit_text(text=f"{LEXICON_RU['select_engine_type']}", reply_markup=create_engine_type_keyboard())
        await state.set_state(CalculatorFSM.engine_type)
    elif current_state == CalculatorFSM.country:
        await callback.message.edit_text(text=f"{LEXICON_RU['select_engine_type']}", reply_markup=create_engine_type_keyboard())
        await state.set_state(CalculatorFSM.engine_type)
    elif current_state == CalculatorFSM.volume:
        await callback.message.edit_text(text=LEXICON_RU['select_country'], reply_markup=create_country_keyboard())
        await state.set_state(CalculatorFSM.country)
    elif current_state == CalculatorFSM.power:
        if data.get('hybrid_type') == 'sequential_hybrid':
            await callback.message.edit_text(text=LEXICON_RU['select_hybrid_type'], reply_markup=create_hybrid_type_keyboard())
            await state.set_state(CalculatorFSM.hybrid_type)
        else:
            await callback.message.edit_text(text=LEXICON_RU['select_country'], reply_markup=create_country_keyboard())
            await state.set_state(CalculatorFSM.country)
    elif current_state == CalculatorFSM.cost:
        if data.get('engine_type') == 'electro' or data.get('hybrid_type') == 'sequential_hybrid':
            await callback.message.edit_text(text=LEXICON_RU['enter_power'], reply_markup=create_cost_keyboard())
            await state.set_state(CalculatorFSM.power)
        else:
            await callback.message.edit_text(text=LEXICON_RU['select_volume'], reply_markup=create_volume_keyboard())
            await state.set_state(CalculatorFSM.volume)
    elif current_state == CalculatorFSM.is_from_kazan:
        currency_text = COUNTRY_INFO.get(data['country'], {}).get('name', '')
        await callback.message.edit_text(text=f"{LEXICON_RU['enter_cost']} {currency_text}", reply_markup=create_cost_keyboard())
        await state.set_state(CalculatorFSM.cost)

    await callback.answer()

@calculator_router.callback_query(StateFilter(CalculatorFSM.year))
async def process_year_sent(callback: CallbackQuery, state: FSMContext):
    year_category = callback.data
    year_display = LEXICON_RU.get(year_category, year_category)
    await state.update_data(year=year_category, original_year=year_display) 
    await callback.message.edit_text(
        text=f"{LEXICON_RU['select_engine_type']}",
        reply_markup=create_engine_type_keyboard()
    )
    await callback.answer()
    await state.set_state(CalculatorFSM.engine_type)

@calculator_router.callback_query(StateFilter(CalculatorFSM.engine_type))
async def process_engine_type_press(callback: CallbackQuery, state: FSMContext):
    engine_type = callback.data
    await state.update_data(engine_type=engine_type)
    if engine_type == 'hybrid':
        await callback.message.edit_text(
            text=LEXICON_RU['select_hybrid_type'],
            reply_markup=create_hybrid_type_keyboard()
        )
        await state.set_state(CalculatorFSM.hybrid_type)
    else:
        await callback.message.edit_text(
            text=LEXICON_RU['select_country'],
            reply_markup=create_country_keyboard()
        )
        await state.set_state(CalculatorFSM.country)
    await callback.answer()

@calculator_router.callback_query(StateFilter(CalculatorFSM.hybrid_type))
async def process_hybrid_type_press(callback: CallbackQuery, state: FSMContext):
    hybrid_type = callback.data
    await state.update_data(hybrid_type=hybrid_type)
    if hybrid_type == 'sequential_hybrid':
        await state.update_data(engine_type='electro')
    else:
        await state.update_data(engine_type='ice')
    await callback.message.edit_text(
        text=LEXICON_RU['select_country'],
        reply_markup=create_country_keyboard()
    )
    await state.set_state(CalculatorFSM.country)
    await callback.answer()



@calculator_router.callback_query(StateFilter(CalculatorFSM.country))
async def process_country_sent(callback: CallbackQuery, state: FSMContext):
    country = callback.data
    await state.update_data(country=country)
    data = await state.get_data()

    if data['engine_type'] == 'electro' or data.get('hybrid_type') == 'sequential_hybrid':
        await callback.message.edit_text(
            text=LEXICON_RU['enter_power'],
            reply_markup=create_cost_keyboard()
        )
        await state.update_data(prompt_message_id=callback.message.message_id)
        await state.set_state(CalculatorFSM.power)
    else:
        await callback.message.edit_text(
            text=LEXICON_RU['select_volume'],
            reply_markup=create_volume_keyboard()
        )
        await state.update_data(prompt_message_id=callback.message.message_id)
        await state.set_state(CalculatorFSM.volume)
    
    await callback.answer()

@calculator_router.callback_query(StateFilter(CalculatorFSM.is_from_kazan))
async def process_kazan_question_answer(callback: CallbackQuery, state: FSMContext, config: Config):
    answer = callback.data.removeprefix('kazan_')
    await state.update_data(is_from_kazan=answer)
    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    if data['engine_type'] == 'electro':
        await state.update_data(volume=0)

    if prompt_message_id:
        try:
            await callback.message.bot.delete_message(chat_id=callback.message.chat.id, message_id=prompt_message_id)
        except TelegramAPIError: 
            pass
            
    await send_calculation_result(callback, state, config)
    await callback.answer()

@calculator_router.message(StateFilter(CalculatorFSM.power), F.text)
async def process_power_sent(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    power_text = message.text.lower().replace(',', '.')
    
    is_kw = 'квт' in power_text or 'kw' in power_text
    is_hp = 'л.с' in power_text or 'лс' in power_text or 'hp' in power_text

    if not is_kw and not is_hp:
        if prompt_message_id:
            try:
                await message.bot.edit_message_text(
                    text=f"{LEXICON_RU['enter_power']}\n\n{LEXICON_RU['power_units_required']}",
                    chat_id=message.chat.id,
                    message_id=prompt_message_id,
                    reply_markup=create_cost_keyboard()
                )
            except TelegramAPIError as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    await message.answer(LEXICON_RU['power_units_required'])
        else:
            await message.answer(LEXICON_RU['power_units_required'])
        return

    try:
        power_value_kw = None
        power_unit_display = None

        if is_kw:
            power_kw_val = float(re.sub(r'[^0-9.]', '', power_text))
            power_value_kw = power_kw_val
            power_unit_display = 'кВт'
            await state.update_data(power=power_value_kw, power_unit=power_unit_display, power_display=power_kw_val)
        else: 
            power_hp_val = float(re.sub(r'[^0-9.]', '', power_text))
            power_value_kw = power_hp_val * 0.7355
            power_unit_display = 'л.с.'
            await state.update_data(power=power_value_kw, power_unit=power_unit_display, power_display=power_hp_val)


        
        currency_text = COUNTRY_INFO.get(data['country'], {}).get('name', '')
        
        if prompt_message_id:
            await message.bot.edit_message_text(
                text=f"{LEXICON_RU['enter_cost']} {currency_text}",
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=create_cost_keyboard()
            )
        else:
            sent_message = await message.answer(
                text=f"{LEXICON_RU['enter_cost']} {currency_text}",
                reply_markup=create_cost_keyboard()
            )
            await state.update_data(prompt_message_id=sent_message.message_id)

        await state.set_state(CalculatorFSM.cost)
    except (ValueError, TypeError):
        if prompt_message_id:
            await message.bot.edit_message_text(
                text=LEXICON_RU['not_a_number'],
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=create_cost_keyboard()
            )
        else:
            await message.answer(text=LEXICON_RU['not_a_number'])


@calculator_router.message(StateFilter(CalculatorFSM.cost), F.text)
async def process_cost_sent(message: Message, state: FSMContext, config: Config):
    await message.delete()
    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    cost_text = message.text.replace(' ', '').replace(',', '')
    if cost_text.isdigit():
        await state.update_data(cost=int(cost_text))
        data = await state.get_data() 

        if prompt_message_id:
            await message.bot.edit_message_text(
                text=LEXICON_RU['is_from_kazan_question'],
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=create_kazan_question_keyboard()
            )
        else:
            sent_message = await message.answer(
                text=LEXICON_RU['is_from_kazan_question'],
                reply_markup=create_kazan_question_keyboard()
            )
            await state.update_data(prompt_message_id=sent_message.message_id)

        await state.set_state(CalculatorFSM.is_from_kazan)
    else:
        if prompt_message_id:
            await message.bot.edit_message_text(
                text=LEXICON_RU['not_a_number'],
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=create_cost_keyboard()
            )
        else:
            await message.answer(text=LEXICON_RU['not_a_number'])

@calculator_router.message(StateFilter(CalculatorFSM.volume), F.text)
async def process_volume_sent(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    if message.text.isdigit():
        await state.update_data(volume=int(message.text))
        data = await state.get_data() 
        
        currency_text = COUNTRY_INFO.get(data['country'], {}).get('name', '')
        
        if prompt_message_id:
            await message.bot.edit_message_text(
                text=f"{LEXICON_RU['enter_cost']} {currency_text}",
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=create_cost_keyboard()
            )
        else:
            sent_message = await message.answer(
                text=f"{LEXICON_RU['enter_cost']} {currency_text}",
                reply_markup=create_cost_keyboard()
            )
            await state.update_data(prompt_message_id=sent_message.message_id)

        await state.set_state(CalculatorFSM.cost)
    else:
        if prompt_message_id:
            await message.bot.edit_message_text(
                text=LEXICON_RU['not_a_number'],
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                reply_markup=create_volume_keyboard()
            )
        else:
            await message.answer(text=LEXICON_RU['not_a_number'])