from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 Тренировка")],
            [KeyboardButton(text="🔍 Поиск")],
            [KeyboardButton(text="📊 Статистика")],
        ],
        resize_keyboard=True
    )


def train_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Помню",
                    callback_data="train_remember"
                ),
                InlineKeyboardButton(
                    text="❌ Не помню",
                    callback_data="train_forget"
                ),
            ]
        ]
    )


def search_next_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Далее ▶",
                    callback_data="search_next"
                )
            ]
        ]
    )
