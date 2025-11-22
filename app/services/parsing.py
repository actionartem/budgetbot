import re
from typing import Optional, Dict, Any

CURRENCY_KEYWORDS = {
    "RUB": [r"руб(?:лей|ля|ль)?", r"\bр\b", r"rub", r"₽"],
    "CNY": [r"юан(?:ь|я|ей)?", r"cny", r"yuan"],
    "EUR": [r"евро", r"eur", r"€"],
    "USD": [r"доллар(?:ов|а)?", r"usd", r"\$"],
}

CATEGORY_KEYWORDS = {
    "билеты": ["билет", "билеты", "перелет", "перелёт", "самолет", "самолёт", "поезд"],
    "отели": ["отель", "гостиница", "hostel", "airbnb", "апартаменты"],
    "еда": ["еда", "завтрак", "обед", "ужин", "кофе", "кафе", "ресторан", "бар"],
    "транспорт": ["такси", "metro", "метро", "каршеринг", "автобус", "транспорт", "диди", "didid"],
    "покупки": ["сувенир", "шопинг", "покупки", "одежда", "кроссовки", "футболка", "кеды"],
    "досуг": ["музей", "аттракцион", "аттракционы", "развлечения", "экскурсия", "кино"],
}

AMOUNT_REGEX = re.compile(r"(\d+[.,]?\d*)")


def detect_currency(text: str) -> Optional[str]:
    lower = text.lower()
    for code, patterns in CURRENCY_KEYWORDS.items():
        for p in patterns:
            if re.search(p, lower):
                return code
    return None


def detect_category(text: str) -> str:
    lower = text.lower()
    for category, words in CATEGORY_KEYWORDS.items():
        for w in words:
            if w in lower:
                return category
    return "прочее"


def basic_parse_expense_text(text: str) -> Optional[Dict[str, Any]]:
    cleaned = text.replace(" ", "")
    amount_match = AMOUNT_REGEX.search(cleaned)
    if not amount_match:
        return None

    raw_amount = amount_match.group(1).replace(",", ".")
    try:
        amount = float(raw_amount)
    except ValueError:
        return None

    currency = detect_currency(text)
    category = detect_category(text)

    return {
        "amount": amount,
        "currency": currency,
        "category": category,
        "description": text,
        "confidence": 0.6 if currency is None else 0.8,
    }
