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
    create_engine_type_keyboard, create_kazan_question_keyboard, create_hybrid_type_keyboard
)
from services.calculator import calculate_cost
from services.menu_utils import send_start_menu
from config.config import load_calc_config_async, Config

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

COUNTRY_CURRENCY_SYMBOL_MAP = {
    'china': '¥', # Yuan symbol
    'korea': '₩'  # Won symbol
}

async def send_calculation_result(message_or_callback, state: FSMContext, config: Config):
    data = await state.get_data()
    calc_config = await load_calc_config_async()
    
    # Use the category for calculation, but the original year for display
    calc_year = data.get('year') # This is the category, e.g., 'year_3_5'
    display_year = data.get('original_year', calc_year) # Fallback to category if original_year is not present
    
    costs = await calculate_cost(
        calc_year, 
        data['cost'], 
        data['country'], 
        data.get('volume', 0), 
        calc_config, 
        data['engine_type'], 
        data.get('is_from_kazan'), 
        data.get('power', 0)
    )
    
    currency_symbol = COUNTRY_CURRENCY_SYMBOL_MAP.get(data['country'], '')

    # --- Build the new message ---
    
    params_lines = []
    # Car Cost
    if data.get('cost'):
        params_lines.append(f"💰 Стоимость: {data['cost']:,} {currency_symbol}".replace(',', ' ')) # Corrected: Removed unnecessary .replace(',', ' ')
    # Year
    display_month = data.get('month')
    year_str = str(display_year)
    if display_month and isinstance(display_year, int):
        year_str = f"{display_year}-{display_month:02d}"
    params_lines.append(f"📅 Год выпуска: {year_str}")
    # Volume
    if data.get('volume', 0) > 0:
        params_lines.append(f"⚙️ Объём двигателя: {data['volume']} см³")
    # Power
    if data.get('power'):
        power_unit = data.get('power_unit', 'кВт')
        power_display = data.get('power_display', data['power'])
        params_lines.append(f"⚡️ Мощность: {power_display} {power_unit}")

    params_section = "\n".join(params_lines)

    payments_lines = [
        f"🇷🇺 Таможенная пошлина: {round(costs['customs_payments']):,} руб.".replace(',', ' '), # Corrected: Removed unnecessary .replace(',', ' ')
        f"📑 Таможенный сбор: {round(costs['customs_clearance']):,} руб.".replace(',', ' '), # Corrected: Removed unnecessary .replace(',', ' ')
        f"♻️ Утилизационный сбор: {costs['recycling_fee']:,} руб.".replace(',', ' ')
    ]
    if costs.get('excise_tax', 0) > 0:
        payments_lines.insert(2, f"💸 **Акциз: {round(costs['excise_tax']):,} руб.".replace(',', ' ')) # Corrected: Removed unnecessary .replace(',', ' ')
    if costs.get('vat', 0) > 0:
        payments_lines.append(f"📊 НДС: {round(costs['vat']):,} руб.".replace(',', ' ')) # Corrected: Removed unnecessary .replace(',', ' ')

    payments_section = "\n".join(payments_lines)

    total_cost_rub_formatted = f"{round(costs['total_cost_rub']):,}".replace(',', ' ') # Corrected: Removed unnecessary .replace(',', ' ')
    
    output_text = (
        f"📋<b>Итоги расчёта для вашего авто</b>📋 \n\n"
        f"<b>Параметры:</b>\n\n{params_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Расчётные платежи:</b>\n\n{payments_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Итого:</b> <code><b>{total_cost_rub_formatted}</b></code> руб."
    )

    if isinstance(message_or_callback, Message):
        target_message = message_or_callback
        user_id = target_message.from_user.id
    else: # it's a CallbackQuery
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
    calc_config = await load_calc_config_async()

    calc_year = data.get('year')
    display_year = data.get('original_year', calc_year)

    costs = await calculate_cost(
        calc_year,
        data['cost'],
        data['country'],
        data.get('volume', 0),
        calc_config,
        data['engine_type'],
        data.get('is_from_kazan'),
        data.get('power', 0)
    )

    currency_symbol = COUNTRY_CURRENCY_SYMBOL_MAP.get(data['country'], '')

    # --- Parameters Section ---
    params_lines = []
    if data.get('cost'):
        params_lines.append(f"💰 Стоимость: {data['cost']:,} {currency_symbol}".replace(',', ' '))
    display_month = data.get('month')
    year_str = str(display_year)
    if display_month and isinstance(display_year, int):
        year_str = f"{display_year}-{display_month:02d}"
    params_lines.append(f"📅 Год выпуска: {year_str}")
    if data.get('volume', 0) > 0:
        params_lines.append(f"⚙️ Объём двигателя: {data['volume']} см³")
    if data.get('power'):
        power_unit = data.get('power_unit', 'кВт')
        power_display = data.get('power_display', data['power'])
        params_lines.append(f"⚡️ Мощность: {power_display} {power_unit}")
    params_section = "\n".join(params_lines)

    # --- Main Payments Section ---
    main_payments_lines = [
        f"🇷🇺 Таможенная пошлина: {round(costs['customs_payments']):,} руб.".replace(',', ' '),
        f"📑 Таможенный сбор: {round(costs['customs_clearance']):,} руб.".replace(',', ' '),
        f"♻️ Утилизационный сбор: {costs['recycling_fee']:,} руб.".replace(',', ' ')
    ]
    if costs.get('excise_tax', 0) > 0:
        main_payments_lines.insert(2, f"💸 Акциз: {round(costs['excise_tax']):,} руб.".replace(',', ' '))
    if costs.get('vat', 0) > 0:
        main_payments_lines.append(f"📊 НДС: {round(costs['vat']):,} руб.".replace(',', ' '))
    main_payments_section = "\n".join(main_payments_lines)

    # --- Additional Expenses Section ---
    additional_expenses_lines = []
    if data['country'] == 'korea':
        additional_expenses_lines.append(f"🇰🇷 Комиссия дилера: {round(costs['dealer_commission']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"🚛 Транспорт по Корее: {round(costs['korea_inland_transport']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"🚢 Погрузка и фрахт: {round(costs['korea_port_transport_loading']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"🇷🇺 Расходы по Владивостоку: {round(costs['vladivostok_expenses']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"🚚 Доставка до вашего города: {round(costs['logistics_vladivostok_kazan']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"🧼 Подготовка авто: {round(costs['car_preparation']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"📎 Прочие расходы: {round(costs['other_expenses']):,} руб.".replace(',', ' '))
    elif data['country'] == 'china':
        additional_expenses_lines.append(f"🇨🇳 Комиссия дилера: {round(costs['dealer_commission']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"📦 Доставка документов: {round(costs['china_documents_delivery']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"🚚 Логистика: {round(costs['logistics_cost']):,} руб.".replace(',', ' '))
        if costs.get('lab_svh_cost', 0) > 0:
            additional_expenses_lines.append(f"🔬 Лаборатория и СВХ: {round(costs['lab_svh_cost']):,} руб.".replace(',', ' '))
        additional_expenses_lines.append(f"📎 Прочие расходы: {round(costs['other_expenses']):,} руб.".replace(',', ' '))

    if costs.get('delivery_to_region_cost', 0) > 0:
        label = LEXICON_RU['lab_svh_not_kazan_rub']
        additional_expenses_lines.append(f"🔬 {label}: {round(costs['delivery_to_region_cost']):,} руб.".replace(',', ' '))
    
    additional_expenses_section = "\n".join(additional_expenses_lines)
    country_name = "Корея" if data['country'] == 'korea' else "Китай"

    total_cost_rub_formatted = f"{round(costs['total_cost_rub']):,}".replace(',', ' ')

    # --- Build Final Message ---
    output_text = (
        f"📋<b>Детальный расчёт для вашего авто</b>📋\n\n"
        f"<b>Параметры:</b>\n\n{params_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Основные платежи:</b>\n\n{main_payments_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Дополнительные расходы ({country_name}):</b>\n\n{additional_expenses_section}\n\n"
        f"⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
        f"<b>Итоговая стоимость:</b> <code>{total_cost_rub_formatted}</code> руб.

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
        await callback.message.delete()
        await send_start_menu(callback.message, state)
    elif current_state == CalculatorFSM.engine_type:
        await callback.message.edit_text(text=LEXICON_RU['select_year'], reply_markup=create_year_keyboard())
        await state.set_state(CalculatorFSM.year)
    elif current_state == CalculatorFSM.hybrid_type:
        await callback.message.edit_text(text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}", reply_markup=create_engine_type_keyboard())
        await state.set_state(CalculatorFSM.engine_type)
    elif current_state == CalculatorFSM.country:
        await callback.message.edit_text(text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}", reply_markup=create_engine_type_keyboard())
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
        currency_text = COUNTRY_CURRENCY_MAP.get(data['country'], '')
        await callback.message.edit_text(text=f"{LEXICON_RU['enter_cost']} {currency_text}", reply_markup=create_cost_keyboard())
        await state.set_state(CalculatorFSM.cost)

    await callback.answer()

@calculator_router.callback_query(StateFilter(CalculatorFSM.year))
async def process_year_sent(callback: CallbackQuery, state: FSMContext):
    year_category = callback.data
    year_display = LEXICON_RU.get(year_category, year_category)
    await state.update_data(year=year_category, original_year=year_display) # Use original_year to store the display text
    await callback.message.edit_text(
        text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}",
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

COUNTRY_CURRENCY_MAP = {
    'china': 'юанях',
    'korea': 'вонах'
}

@calculator_router.callback_query(StateFilter(CalculatorFSM.country))
async def process_country_sent(callback: CallbackQuery, state: FSMContext):
    country = callback.data
    await state.update_data(country=country)
    data = await state.get_data()

    if data['engine_type'] == 'electro' or data.get('hybrid_type') == 'sequential_hybrid':
        await callback.message.edit_text(
            text=LEXICON_RU['enter_power'],
            reply_markup=create_cost_keyboard() # Reuse cost keyboard for back button
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
        except TelegramAPIError: # message might be already deleted
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
            await state.update_data(power_display=power_kw_val)
        else: # is_hp
            power_hp_val = float(re.sub(r'[^0-9.]', '', power_text))
            power_value_kw = power_hp_val * 0.7355
            power_unit_display = 'л.с.'
            await state.update_data(power_display=power_hp_val)

        await state.update_data(power=power_value_kw, power_unit=power_unit_display)
        data = await state.get_data() # re-get data
        
        currency_text = COUNTRY_CURRENCY_MAP.get(data['country'], '')
        
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
                reply_markup=create_cost_keyboard() # Reuse cost keyboard for back button
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
        data = await state.get_data() # Re-get data to include updated cost

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
        data = await state.get_data() # re-get data
        
        currency_text = COUNTRY_CURRENCY_MAP.get(data['country'], '')
        
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
