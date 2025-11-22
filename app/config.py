import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://budgetbot_user:password@localhost:5432/budgetbot_db",
    )
    base_currency: str = os.getenv("BASE_CURRENCY", "RUB")
    currency_api_url: str = os.getenv(
        "CURRENCY_API_URL",
        "https://api.exchangerate.host/latest",
    )


settings = Settings()
