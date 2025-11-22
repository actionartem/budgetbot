# BudgetBot

Телеграм-бот для подсчёта бюджета по проектам (поездки, ремонты, отдых).

## Стек

- Python 3.10+
- aiogram 3
- PostgreSQL
- SQLAlchemy Core
- Alembic
- OpenAI API (опционально, для умного парсинга и резюме отчётов)

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/budgetbot.git
cd budgetbot
```

### 2. Виртуальное окружение и зависимости

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Настроить PostgreSQL

Создать БД и пользователя, например:

```sql
CREATE USER budgetbot_user WITH PASSWORD 'your_password';
CREATE DATABASE budgetbot_db OWNER budgetbot_user;
GRANT ALL PRIVILEGES ON DATABASE budgetbot_db TO budgetbot_user;
```

### 4. Настроить `.env`

Скопировать:

```bash
cp .env.example .env
```

Заполнить:

- `TELEGRAM_BOT_TOKEN` — токен бота из BotFather
- `OPENAI_API_KEY` — ключ OpenAI (если нужен GPT)
- `DATABASE_URL` — строка подключения к БД

### 5. Прогнать миграции

```bash
alembic upgrade head
```

### 6. Локальный запуск

```bash
source venv/bin/activate
python -m app.main
```

Бот начнёт слушать апдейты через long polling.

---

## Деплой на VPS (Ubuntu)

1. Склонировать репозиторий в `/srv/budgetbot`:

```bash
cd /srv
sudo mkdir budgetbot
sudo chown $USER:$USER budgetbot
cd budgetbot
git clone https://github.com/YOUR_USERNAME/budgetbot.git .
```

2. Виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Настроить `.env`:

```bash
cp .env.example .env
nano .env
```

4. Прогнать миграции:

```bash
alembic upgrade head
```

5. Создать systemd-сервис:

```bash
sudo nano /etc/systemd/system/budgetbot.service
```

Пример:

```ini
[Unit]
Description=Budget Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/srv/budgetbot
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/srv/budgetbot/.env
ExecStart=/srv/budgetbot/venv/bin/python -m app.main
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

6. Запустить:

```bash
sudo systemctl daemon-reload
sudo systemctl enable budgetbot
sudo systemctl start budgetbot
sudo systemctl status budgetbot
```

Если статус `active (running)` — бот запущен и переживёт перезагрузку сервера.
