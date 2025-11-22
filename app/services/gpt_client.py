import asyncio
import json
from typing import Optional, Dict, Any

import openai

from app.config import settings

openai.api_key = settings.openai_api_key

PARSE_SYSTEM_PROMPT = (
    "Ты — парсер финансовых расходов для Telegram-бота. "
    "Твоя задача — из обычного текста пользователя вытащить информацию о трате.\n\n"
    "Всегда возвращай ЖЁСТКО валидный JSON без пояснений и форматирования, без текста до и после.\n"
    "Структура JSON:\n"
    "{\n"
    "  \"amount\": float | null,\n"
    "  \"currency\": string | null,\n"
    "  \"category\": string | null,\n"
    "  \"description\": string,\n"
    "  \"confidence\": float\n"
    "}\n\n"
    "Правила:\n"
    "- Если валюта явно не указана, оставь \"currency\": null.\n"
    "- Если сумма не найдена — \"amount\": null.\n"
    "- Категорию определяй по смыслу:\n"
    "  - \"билеты\", \"перелёт\", \"самолёт\", \"поезд\" -> \"билеты\"\n"
    "  - \"отель\", \"гостиница\", \"airbnb\" -> \"отели\"\n"
    "  - \"еда\", \"завтрак\", \"обед\", \"ужин\", \"кофе\", \"кафе\", \"ресторан\" -> \"еда\"\n"
    "  - \"такси\", \"метро\", \"дидиди\", \"каршеринг\", \"транспорт\" -> \"транспорт\"\n"
    "  - \"сувенир\", \"шопинг\", \"покупки\", \"одежда\", \"кроссовки\", \"футболка\" -> \"покупки\"\n"
    "  - \"музей\", \"аттракционы\", \"развлечения\", \"экскурсия\" -> \"досуг\"\n"
    "  - иначе -> \"прочее\"\n"
    "- Поддерживай распознавание валют:\n"
    "  - рубль: \"руб\", \"рублей\", \"р\", \"RUB\", \"₽\" -> \"RUB\"\n"
    "  - юань: \"юань\", \"юаней\", \"юаня\", \"CNY\", \"yuan\" -> \"CNY\"\n"
    "  - евро: \"евро\", \"EUR\", \"€\" -> \"EUR\"\n"
    "  - доллар: \"доллар\", \"долларов\", \"USD\", \"$\" -> \"USD\"\n"
    "- \"description\" всегда равен исходному тексту пользователя без изменений.\n"
    "- Если данных мало или они противоречивы — ставь низкий \"confidence\", например 0.3–0.5.\n\n"
    "Отвечай ТОЛЬКО JSON-объектом без комментариев и без лишнего текста."
)


async def gpt_parse_expense(text: str) -> Optional[Dict[str, Any]]:
    if not settings.openai_api_key:
        return None

    loop = asyncio.get_running_loop()

    def _call():
        resp = openai.ChatCompletion.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": f'Разбери эту трату:\n\nтекст: "{text}"'},
            ],
        )
        return resp["choices"][0]["message"]["content"]

    content = await loop.run_in_executor(None, _call)

    try:
        data = json.loads(content)
        return data
    except Exception:
        return None


async def gpt_summarize_report(structured: Dict[str, Any]) -> Optional[str]:
    if not settings.openai_api_key:
        return None

    loop = asyncio.get_running_loop()

    def _call():
        resp = openai.ChatCompletion.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты помогаешь кратко и по делу описать структуру расходов пользователя. "
                        "Не больше 3–4 предложений, без воды, на русском языке."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(structured, ensure_ascii=False),
                },
            ],
        )
        return resp["choices"][0]["message"]["content"]

    content = await loop.run_in_executor(None, _call)
    return content.strip()
