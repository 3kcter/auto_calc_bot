from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup

from lexicon.lexicon import LEXICON_RU
from keyboards.admin_keyboards import (
    create_admin_country_keyboard,
    create_china_admin_menu_keyboard,
    create_korea_admin_menu_keyboard,
    create_edit_keyboard
)
from config.config import load_calc_config, save_calc_config, Config

admin_router = Router()

class AdminFSM(StatesGroup):
    menu = State()
    edit_param = State()
    select_country = State()

@admin_router.message(Command("admin"))
async def process_admin_command(message: Message, state: FSMContext, config: Config):
    if message.from_user.id in config.bot.admin_ids:
        await message.answer(
            text=LEXICON_RU['admin_panel'],
            reply_markup=create_admin_country_keyboard()
        )
        await state.set_state(AdminFSM.select_country)

@admin_router.callback_query(F.data == 'exit_admin', StateFilter(AdminFSM.select_country))
async def process_exit_admin_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()

@admin_router.callback_query(F.data == 'admin_china', StateFilter(AdminFSM.select_country))
async def process_admin_china_press(callback: CallbackQuery, state: FSMContext):
    calc_config = load_calc_config()
    await callback.message.edit_text(
        text=LEXICON_RU['admin_panel'],
        reply_markup=create_china_admin_menu_keyboard(calc_config)
    )
    await state.set_state(AdminFSM.menu)

@admin_router.callback_query(F.data == 'admin_korea', StateFilter(AdminFSM.select_country))
async def process_admin_korea_press(callback: CallbackQuery, state: FSMContext):
    calc_config = load_calc_config()
    await callback.message.edit_text(
        text=LEXICON_RU['admin_panel'],
        reply_markup=create_korea_admin_menu_keyboard(calc_config)
    )
    await state.set_state(AdminFSM.menu)

@admin_router.callback_query(F.data == 'back_to_country_select', StateFilter(AdminFSM.menu))
async def process_back_to_country_select_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        text=LEXICON_RU['admin_panel'],
        reply_markup=create_admin_country_keyboard()
    )
    await state.set_state(AdminFSM.select_country)

@admin_router.callback_query(F.data.startswith('edit_'), StateFilter(AdminFSM.menu))
async def process_edit_press(callback: CallbackQuery, state: FSMContext):
    param_to_edit = callback.data.removeprefix('edit_')
    country, field = param_to_edit.split('_', 1)
    await state.update_data(param_to_edit=param_to_edit)
    await callback.message.edit_text(
        text=f"{LEXICON_RU['enter_new_value']} {LEXICON_RU['calc_config_fields'][country][field]}:",
        reply_markup=create_edit_keyboard(param_to_edit)
    )
    await state.set_state(AdminFSM.edit_param)

@admin_router.callback_query(F.data.startswith('back_admin_'), StateFilter(AdminFSM.edit_param))
async def process_back_admin_press(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split('_')[-1]
    calc_config = load_calc_config()
    if country == 'china':
        await callback.message.edit_text(
            text=LEXICON_RU['admin_panel'],
            reply_markup=create_china_admin_menu_keyboard(calc_config)
        )
    else:
        await callback.message.edit_text(
            text=LEXICON_RU['admin_panel'],
            reply_markup=create_korea_admin_menu_keyboard(calc_config)
        )
    await state.set_state(AdminFSM.menu)

@admin_router.message(StateFilter(AdminFSM.edit_param), F.text)
async def process_new_value_sent(message: Message, state: FSMContext):
    data = await state.get_data()
    param_to_edit = data.get('param_to_edit')
    country, field = param_to_edit.split('_', 1)
    new_value = message.text

    if new_value.isdigit():
        calc_config = load_calc_config()
        country_config = getattr(calc_config, country)
        setattr(country_config, field, int(new_value))
        save_calc_config(calc_config)

        await message.answer(text=LEXICON_RU['value_updated'])
        calc_config = load_calc_config()
        if country == 'china':
            await message.answer(
                text=LEXICON_RU['admin_panel'],
                reply_markup=create_china_admin_menu_keyboard(calc_config)
            )
        else:
            await message.answer(
                text=LEXICON_RU['admin_panel'],
                reply_markup=create_korea_admin_menu_keyboard(calc_config)
            )
        await state.set_state(AdminFSM.menu)
    else:
        await message.answer(text=LEXICON_RU['not_a_number'])
