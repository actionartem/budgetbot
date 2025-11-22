from aiogram import Router, types
from aiogram.filters import CommandStart

from app.keyboards.main_menu import main_menu_kb

router = Router()


def register(dp):
    dp.include_router(router)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    text = (
        "Привет! Я бот для подсчёта бюджета по разным проектам (поездка, ремонт, отпуск и т.д.).\n\n"
        "Главное меню:\n"
        "• <b>Новый проект</b> — создать проект и сразу сделать его активным.\n"
        "• <b>Список проектов</b> — выбрать, какой проект сделать активным.\n"
        "• <b>Удалить проект</b> — удалить один из проектов без подтверждения.\n"
        "• <b>Получить сводку по текущему проекту</b> — отчёт и краткий текстовый разбор.\n\n"
        "Также доступны команды:\n"
        "/newproject — создать проект\n"
        "/projects — список проектов и выбор активного\n"
        "/report — отчёт по текущему проекту"
    )
    await message.answer(text, reply_markup=main_menu_kb())
