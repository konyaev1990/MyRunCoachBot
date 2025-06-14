
# MyRunCoachBot (финальная сборка)

## Установка зависимостей
pip install -r requirements.txt

## Запуск локально
python bot.py

## Для деплоя на Render:
- Web Service (Free Plan)
- Build Command не нужен
- Start Command: web: gunicorn bot:app
- Обязательно указать переменную окружения: BOT_TOKEN

