from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import (
    create_year_keyboard, create_cost_keyboard, create_volume_keyboard,
    create_country_keyboard, create_after_calculation_keyboard,
    create_engine_type_keyboard, create_kazan_question_keyboard
)
from services.calculator import calculate_cost
from services.menu_utils import send_start_menu
from config.config import load_calc_config_async, Config

calculator_router = Router()

class CalculatorFSM(StatesGroup):
    year = State()
    engine_type = State()
    country = State()
    is_from_kazan = State()
    cost = State()
    volume = State()
    url = State()
    result = State()

COUNTRY_CURRENCY_SYMBOL_MAP = {
    'china': '¥', # Yuan symbol
    'korea': '₩'  # Won symbol
}

async def send_calculation_result(message_or_callback, state: FSMContext, config: Config):
    data = await state.get_data()
    calc_config = await load_calc_config_async()
    costs = await calculate_cost(data['year'], data['cost'], data['country'], data.get('volume', 0), calc_config, data['engine_type'], data.get('is_from_kazan'))
    
    year_display_text = data.get('age_category', LEXICON_RU.get(data['year'], data['year']))
    engine_type_text = LEXICON_RU.get(data['engine_type'], data['engine_type'])

    currency_symbol = COUNTRY_CURRENCY_SYMBOL_MAP.get(data['country'], '')

    output_text = (
        f"{LEXICON_RU['calculation_params']}:\n"
        f"🔹 {LEXICON_RU['car_age']}: {year_display_text}\n"
        f"🔹 {LEXICON_RU['engine_type_label']}: {engine_type_text}\n"
        f"🔹 {LEXICON_RU['car_cost']}: {data['cost']:,} {currency_symbol}\n"
    )
    
    if data['engine_type'] == 'electro' and data.get('power', 0) > 0:
        output_text += f"🔹 {LEXICON_RU['power']}: {data['power']} кВт⋅ч\n\n"
    elif data.get('volume', 0) > 0:
        output_text += f"🔹 {LEXICON_RU['engine_volume']}: {data.get('volume', 0)} куб. см.\n\n"
    else:
        output_text += "\n" # Add a newline if engine volume is not displayed, to maintain spacing

    output_text += (
        f"🔸 {LEXICON_RU['customs_payments']}: {round(costs['customs_payments']):,} руб.\n"
        f"🔸 {LEXICON_RU['customs_clearance']}: {round(costs['customs_clearance']):,} руб.\n"
        f"🔸 {LEXICON_RU['recycling_fee']}: {costs['recycling_fee']:,} руб.\n"
    )

    if costs['vat'] > 0:
        output_text += f"\n🔸 {LEXICON_RU['vat']}: {round(costs['vat']):,} руб."

    output_text += f"\n\n{LEXICON_RU['total_cost']}: {round(costs['total_cost']):,} {currency_symbol} ({round(costs['total_cost_rub']):,} руб.)"

    if isinstance(message_or_callback, Message):
        target_message = message_or_callback
        user_id = target_message.from_user.id
    else: # it's a CallbackQuery
        target_message = message_or_callback.message
        user_id = message_or_callback.from_user.id

    is_admin = user_id in config.bot.admin_ids

    await target_message.answer(
        text=output_text,
        reply_markup=create_after_calculation_keyboard(is_admin=is_admin)
    )
    await state.set_state(CalculatorFSM.result)

@calculator_router.callback_query(F.data == 'detailed_calculation', StateFilter(CalculatorFSM.result))
async def process_detailed_calculation_press(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    calc_config = await load_calc_config_async()
    costs = await calculate_cost(data['year'], data['cost'], data['country'], data.get('volume', 0), calc_config, data['engine_type'], data.get('is_from_kazan'))

    detailed_output_text = f"{LEXICON_RU['calculation_params']}:\n"
    detailed_output_text += f"🔹 {LEXICON_RU['car_age']}: {data.get('age_category', LEXICON_RU.get(data['year'], data['year']))}\n"
    detailed_output_text += f"🔹 {LEXICON_RU['engine_type_label']}: {LEXICON_RU.get(data['engine_type'], data['engine_type'])}\n"
    detailed_output_text += f"🔹 {LEXICON_RU['car_cost']}: {data['cost']:,} {COUNTRY_CURRENCY_SYMBOL_MAP.get(data['country'], '')}\n"
    
    if data['engine_type'] == 'electro' and data.get('power', 0) > 0:
        detailed_output_text += f"🔹 {LEXICON_RU['power']}: {data['power']} кВт⋅ч\n\n"
    elif data.get('volume', 0) > 0:
        detailed_output_text += f"🔹 {LEXICON_RU['engine_volume']}: {data.get('volume', 0)} куб. см.\n\n"
    else:
        detailed_output_text += "\n" # Add a newline if engine volume is not displayed, to maintain spacing

    if data['engine_type'] == 'electro':
        detailed_output_text += f"🔸 {LEXICON_RU['customs_payments']} (15%): {round(costs['customs_payments']):,} руб.\n"
    else:
        detailed_output_text += f"🔸 {LEXICON_RU['customs_payments']}: {round(costs['customs_payments']):,} руб.\n"

    detailed_output_text += f"🔸 {LEXICON_RU['customs_clearance']}: {round(costs['customs_clearance']):,} руб.\n"
    detailed_output_text += f"🔸 {LEXICON_RU['recycling_fee']}: {costs['recycling_fee']:,} руб.\n"


    if data['country'] == 'korea':
        detailed_output_text += f"🔸 {LEXICON_RU['dealer_commission']}: {costs['dealer_commission']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['korea_inland_transport']}: {costs['korea_inland_transport']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['korea_port_transport_loading']}: {costs['korea_port_transport_loading']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['vladivostok_expenses']}: {costs['vladivostok_expenses']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['logistics_vladivostok_kazan']}: {costs['logistics_vladivostok_kazan']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['car_preparation']}: {costs['car_preparation']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['other_expenses']}: {costs['other_expenses']:,} руб.\n"
    elif data['country'] == 'china':
        detailed_output_text += f"🔸 {LEXICON_RU['dealer_commission']}: {costs['dealer_commission']:,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['china_documents_delivery']}: {round(costs['china_documents_delivery']):,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['logistics_cost']}: {round(costs['logistics_cost']):,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['lab_svh_cost']}: {round(costs['lab_svh_cost']):,} руб.\n"
        detailed_output_text += f"🔸 {LEXICON_RU['other_expenses']}: {costs['other_expenses']:,} руб.\n"

    if costs['vat'] > 0:
        detailed_output_text += f"🔸 {LEXICON_RU['vat']}: {round(costs['vat']):,} руб.\n"

    detailed_output_text += f"\n{LEXICON_RU['total_cost']}: {round(costs['total_cost']):,} {COUNTRY_CURRENCY_SYMBOL_MAP.get(data['country'], '')} ({round(costs['total_cost_rub']):,} руб.)"

    await callback.message.answer(text=detailed_output_text)
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
    elif current_state == CalculatorFSM.country:
        await callback.message.edit_text(text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}", reply_markup=create_engine_type_keyboard())
        await state.set_state(CalculatorFSM.engine_type)
    elif current_state == CalculatorFSM.volume:
        await callback.message.edit_text(text=LEXICON_RU['select_country'], reply_markup=create_country_keyboard())
        await state.set_state(CalculatorFSM.country)
    elif current_state == CalculatorFSM.cost:
        if data.get('engine_type') == 'electro':
            await callback.message.edit_text(text=LEXICON_RU['select_country'], reply_markup=create_country_keyboard())
            await state.set_state(CalculatorFSM.country)
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
    await state.update_data(year=callback.data)
    await callback.message.edit_text(
        text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}",
        reply_markup=create_engine_type_keyboard()
    )
    await callback.answer()
    await state.set_state(CalculatorFSM.engine_type)

@calculator_router.callback_query(StateFilter(CalculatorFSM.engine_type))
async def process_engine_type_press(callback: CallbackQuery, state: FSMContext):
    await state.update_data(engine_type=callback.data)
    await callback.message.edit_text(
        text=LEXICON_RU['select_country'],
        reply_markup=create_country_keyboard()
    )
    await callback.answer()
    await state.set_state(CalculatorFSM.country)

COUNTRY_CURRENCY_MAP = {
    'china': 'юанях',
    'korea': 'вонах'
}

@calculator_router.callback_query(StateFilter(CalculatorFSM.country))
async def process_country_sent(callback: CallbackQuery, state: FSMContext):
    country = callback.data
    await state.update_data(country=country)
    data = await state.get_data()

    if data['engine_type'] == 'electro':
        currency_text = COUNTRY_CURRENCY_MAP.get(country, '')
        await callback.message.edit_text(
            text=f"{LEXICON_RU['enter_cost']} {currency_text}",
            reply_markup=create_cost_keyboard()
        )
        await state.update_data(prompt_message_id=callback.message.message_id)
        await state.set_state(CalculatorFSM.cost)
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
