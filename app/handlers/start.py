from aiogram import Router, types
from aiogram.filters import CommandStart, Command

from app.keyboards import main_menu_kb

router = Router()


def register(dp):
    dp.include_router(router)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "Привет! Я бот для подсчёта бюджета по разным проектам (поездка, ремонт, отпуск и т.д.).\n\n"
        "Как использовать:\n"
        "1) Создай проект: /newproject\n"
        "2) Посмотри список проектов: /projects\n"
        "3) Сделай проект активным: /setproject <id>\n"
        "4) Просто присылай траты текстом, например:\n"
        "   • <code>билеты 99000 руб</code>\n"
        "   • <code>отели 65000</code>\n"
        "   • <code>сувенир 10 юаней</code>\n\n"
        "Отчёт по текущему проекту: /report"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await cmd_start(message)
