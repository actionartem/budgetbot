from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_kb() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="Новый проект")],
        [KeyboardButton(text="Список проектов")],
        [KeyboardButton(text="Удалить проект")],
        [KeyboardButton(text="Получить сводку по текущему проекту")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )
