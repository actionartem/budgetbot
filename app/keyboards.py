from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Новый проект")],
            [KeyboardButton(text="Список проектов")],
        ],
        resize_keyboard=True,
    )
    return kb
