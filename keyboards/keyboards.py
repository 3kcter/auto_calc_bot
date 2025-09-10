from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON_RU
from config.config import Config, load_config

config: Config = load_config()

def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['calculator'], callback_data='calculator'),
        InlineKeyboardButton(text=LEXICON_RU['exchange_rates'], callback_data='exchange_rates')
    )
    return builder.as_markup()



def create_year_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['year_less_3'], callback_data='year_less_3'),
        InlineKeyboardButton(text=LEXICON_RU['year_3_5'], callback_data='year_3_5'),
        InlineKeyboardButton(text=LEXICON_RU['year_more_5'], callback_data='year_more_5')
    )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back'),
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit')
    )
    return builder.as_markup()

def create_country_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['china'], callback_data='china'),
        InlineKeyboardButton(text=LEXICON_RU['korea'], callback_data='korea')
    )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back')
    )
    return builder.as_markup()

def create_cost_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back'),
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit')
    )
    return builder.as_markup()

def create_volume_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back'),
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit')
    )
    return builder.as_markup()

def create_after_calculation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['calculate_another_car'], callback_data='calculator')
    )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit')
    )
    return builder.as_markup()


def create_engine_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['ice'], callback_data='ice'),
        InlineKeyboardButton(text=LEXICON_RU['electro'], callback_data='electro')
    )
    builder.row(
        InlineKeyboardButton(text=LEXICON_RU['back'], callback_data='back'),
        InlineKeyboardButton(text=LEXICON_RU['exit'], callback_data='exit')
    )
    return builder.as_markup()

channel_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=LEXICON_RU['channel_button'], url=config.bot.channel_url)]
    ]
)
