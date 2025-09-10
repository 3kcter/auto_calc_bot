from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.fsm.state import State, StatesGroup

from lexicon.lexicon import LEXICON_RU
from keyboards.admin_keyboards import create_admin_menu_keyboard, create_edit_keyboard
from config.config import load_calc_config, save_calc_config, Config

admin_router = Router()

class AdminFSM(StatesGroup):
    menu = State()
    edit_param = State()

@admin_router.message(Command("admin"))
async def process_admin_command(message: Message, state: FSMContext, config: Config):
    if message.from_user.id in config.bot.admin_ids:
        calc_config = load_calc_config()
        await message.answer(
            text=LEXICON_RU['admin_panel'],
            reply_markup=create_admin_menu_keyboard(calc_config)
        )
        await state.set_state(AdminFSM.menu)

@admin_router.callback_query(F.data == 'exit_admin', StateFilter(AdminFSM.menu))
async def process_exit_admin_press(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()

@admin_router.callback_query(F.data.startswith('edit_'), StateFilter(AdminFSM.menu))
async def process_edit_press(callback: CallbackQuery, state: FSMContext):
    param_to_edit = callback.data.split('_')[-1]
    await state.update_data(param_to_edit=param_to_edit)
    await callback.message.edit_text(
        text=f"{LEXICON_RU['enter_new_value']} "{LEXICON_RU['calc_config_fields'][param_to_edit]}":",
        reply_markup=create_edit_keyboard(param_to_edit)
    )
    await state.set_state(AdminFSM.edit_param)

@admin_router.callback_query(F.data == 'back_admin', StateFilter(AdminFSM.edit_param))
async def process_back_admin_press(callback: CallbackQuery, state: FSMContext):
    calc_config = load_calc_config()
    await callback.message.edit_text(
        text=LEXICON_RU['admin_panel'],
        reply_markup=create_admin_menu_keyboard(calc_config)
    )
    await state.set_state(AdminFSM.menu)

@admin_router.message(StateFilter(AdminFSM.edit_param), F.text)
async def process_new_value_sent(message: Message, state: FSMContext):
    data = await state.get_data()
    param_to_edit = data.get('param_to_edit')
    new_value = message.text

    if new_value.isdigit():
        calc_config = load_calc_config()
        setattr(calc_config, param_to_edit, int(new_value))
        save_calc_config(calc_config)

        await message.answer(text=LEXICON_RU['value_updated'])
        calc_config = load_calc_config()
        await message.answer(
            text=LEXICON_RU['admin_panel'],
            reply_markup=create_admin_menu_keyboard(calc_config)
        )
        await state.set_state(AdminFSM.menu)
    else:
        await message.answer(text=LEXICON_RU['not_a_number'])
