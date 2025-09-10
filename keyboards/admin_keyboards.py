from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON_RU
from config.config import CalcConfig

def create_admin_menu_keyboard(calc_config: CalcConfig) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, name in LEXICON_RU['calc_config_fields'].items():
        builder.row(
            InlineKeyboardButton(text=f"{name}: {getattr(calc_config, field)}", callback_data=f"edit_{field}")
        )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit_admin')
    )
    return builder.as_markup()

def create_edit_keyboard(field: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back_admin')
    )
    return builder.as_markup()
