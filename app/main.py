import asyncio

from .bot import bot, dp
from .handlers import start, projects, expenses, reports


def register_handlers():
    start.register(dp)
    projects.register(dp)
    expenses.register(dp)
    reports.register(dp)


async def main():
    register_handlers()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
