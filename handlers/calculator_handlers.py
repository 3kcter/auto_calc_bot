from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup

from lexicon.lexicon import LEXICON_RU
from keyboards.keyboards import (
    create_year_keyboard, create_cost_keyboard, create_volume_keyboard,
    create_currency_keyboard, create_after_calculation_keyboard,
    create_engine_type_keyboard
)
from services.calculator import calculate_cost
from handlers.common_handlers import send_start_menu
from config.config import load_calc_config

calculator_router = Router()

class CalculatorFSM(StatesGroup):
    year = State()
    engine_type = State()
    currency = State()
    cost = State()
    volume = State()
    url = State()
    result = State()

async def send_calculation_result(message_or_callback, state: FSMContext):
    data = await state.get_data()
    calc_config = load_calc_config()
    costs = await calculate_cost(data['year'], data['cost'], data['currency'], data.get('volume', 0), calc_config, data['engine_type'])
    
    year_text = LEXICON_RU.get(data['year'], data['year'])
    engine_type_text = LEXICON_RU.get(data['engine_type'], data['engine_type'])

    output_text = \
        f"{LEXICON_RU['calculation_params']}:\n" \
        f"{LEXICON_RU['car_age']}: {year_text}\n" \
        f"{LEXICON_RU['engine_type_label']}: {engine_type_text}\n" \
        f"{LEXICON_RU['car_cost']}: {data['cost']:,} {data['currency']}\n" \
        f"{LEXICON_RU['engine_volume']}: {data.get('volume', 0)} куб. см.\n\n" \
        f"{LEXICON_RU['customs_payments']}: {round(costs['customs_payments']):,} руб.\n" \
        f"{LEXICON_RU['recycling_fee']}: {costs['recycling_fee']:,} руб.\n" \
        f"{LEXICON_RU['customs_clearance']}: {round(costs['customs_clearance']):,} руб.\n"

    if costs['vat'] > 0:
        output_text += f"\n{LEXICON_RU['vat']}: {round(costs['vat']):,} руб."

    output_text += f"\n\n{LEXICON_RU['total_cost']}: {round(costs['total_cost']):,} руб."

    target_message = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message

    await target_message.answer(
        text=output_text,
        reply_markup=create_after_calculation_keyboard()
    )
    await state.set_state(CalculatorFSM.result)

@calculator_router.callback_query(F.data == 'calculator')
async def process_calculator_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        text=LEXICON_RU['select_year'],
        reply_markup=create_year_keyboard()
    )
    await state.set_state(CalculatorFSM.year)
    await callback.answer()

@calculator_router.callback_query(F.data == 'back')
async def process_back_press(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == CalculatorFSM.year:
        await callback.message.delete()
        await send_start_menu(callback.message, state)
    elif current_state == CalculatorFSM.engine_type:
        await callback.message.edit_text(
            text=LEXICON_RU['select_year'],
            reply_markup=create_year_keyboard()
        )
        await state.set_state(CalculatorFSM.year)
    elif current_state == CalculatorFSM.currency:
        await callback.message.edit_text(
            text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}",
            reply_markup=create_engine_type_keyboard()
        )
        await state.set_state(CalculatorFSM.engine_type)
    elif current_state == CalculatorFSM.cost:
        await callback.message.edit_text(
            text=LEXICON_RU['select_currency'],
            reply_markup=create_currency_keyboard()
        )
        await state.set_state(CalculatorFSM.currency)
    elif current_state == CalculatorFSM.volume:
        await callback.message.edit_text(
            text=LEXICON_RU['enter_cost'],
            reply_markup=create_cost_keyboard()
        )
        await state.set_state(CalculatorFSM.cost)
    await callback.answer()

@calculator_router.callback_query(StateFilter(CalculatorFSM.year))
async def process_year_sent(callback: CallbackQuery, state: FSMContext):
    await state.update_data(year=callback.data)
    await callback.message.delete()
    await callback.message.answer(
        text=f"{LEXICON_RU['select_engine_type']}\n\n{LEXICON_RU['hybrid_info']}",
        reply_markup=create_engine_type_keyboard()
    )
    await callback.answer()
    await state.set_state(CalculatorFSM.engine_type)

@calculator_router.callback_query(StateFilter(CalculatorFSM.engine_type))
async def process_engine_type_press(callback: CallbackQuery, state: FSMContext):
    await state.update_data(engine_type=callback.data)
    await callback.message.delete()
    await callback.message.answer(
        text=LEXICON_RU['select_currency'],
        reply_markup=create_currency_keyboard()
    )
    await callback.answer()
    await state.set_state(CalculatorFSM.currency)

@calculator_router.callback_query(StateFilter(CalculatorFSM.currency))
async def process_currency_sent(callback: CallbackQuery, state: FSMContext):
    await state.update_data(currency=callback.data)
    await callback.message.delete()
    sent_message = await callback.message.answer(
        text=LEXICON_RU['enter_cost'],
        reply_markup=create_cost_keyboard()
    )
    await state.update_data(prompt_message_id=sent_message.message_id)
    await callback.answer()
    await state.set_state(CalculatorFSM.cost)

@calculator_router.message(StateFilter(CalculatorFSM.cost), F.text)
async def process_cost_sent(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')

    cost_text = message.text.replace(' ', '').replace(',', '')
    if cost_text.isdigit():
        await state.update_data(cost=int(cost_text))
        data = await state.get_data()
        
        if data['engine_type'] == 'electro':
            await state.update_data(volume=0)
            if prompt_message_id:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
            await send_calculation_result(message, state)
        else:
            if prompt_message_id:
                await message.bot.edit_message_text(
                    text=LEXICON_RU['select_volume'],
                    chat_id=message.chat.id,
                    message_id=prompt_message_id,
                    reply_markup=create_volume_keyboard()
                )
            else:
                 await message.answer(
                    text=LEXICON_RU['select_volume'],
                    reply_markup=create_volume_keyboard()
                )
            await state.set_state(CalculatorFSM.volume)
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
    if message.text.isdigit():
        await state.update_data(volume=int(message.text))
        data = await state.get_data()
        prompt_message_id = data.get('prompt_message_id')
        if prompt_message_id:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
        await message.delete()
        await send_calculation_result(message, state)
    else:
        await message.answer(text=LEXICON_RU['not_a_number'])
