from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON_RU
from config.config import UserCalcConfig

def create_admin_country_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['china'], callback_data='admin_china'),
        InlineKeyboardButton(text=LEXICON_RU['korea'], callback_data='admin_korea')
    )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit_admin')
    )
    return builder.as_markup()

def create_china_admin_menu_keyboard(calc_config: UserCalcConfig) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, name in LEXICON_RU['calc_config_fields']['china'].items():
        builder.row(
            InlineKeyboardButton(text=f"{name}: {getattr(calc_config.china, field)}", callback_data=f"edit_china_{field}")
        )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back_to_country_select')
    )
    return builder.as_markup()

def create_korea_admin_menu_keyboard(calc_config: UserCalcConfig) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for field, name in LEXICON_RU['calc_config_fields']['korea'].items():
        builder.row(
            InlineKeyboardButton(text=f"{name}: {getattr(calc_config.korea, field)}", callback_data=f"edit_korea_{field}")
        )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back_to_country_select')
    )
    return builder.as_markup()

def create_edit_keyboard(field: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    country = field.split('_')[1]
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data=f'back_admin_{country}')
    )
    return builder.as_markup()