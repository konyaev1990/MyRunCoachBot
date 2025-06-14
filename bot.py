import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")  # Установите переменную окружения
WEBHOOK_URL = f"https://{os.getenv('DOMAIN')}/{TOKEN}"   # Например, mybot.onrender.com

# Инициализация приложений
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# Пример команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот, работающий на веб-сервере.")

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))

# Webhook маршрут
@app.post(f"/{TOKEN}")
async def telegram_webhook():
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        await application.update_queue.put(update)
        return '', 200
    except Exception as e:
        logger.error(f"Ошибка webhook: {e}")
        return '', 500

@app.get("/")
async def health_check():
    return "Бот работает!", 200

# Инициализация webhook
async def set_webhook():
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)

# Точка входа для WSGI-совместимого сервера
def main():
    import asyncio
    from hypercorn.asyncio import serve
    from hypercorn.config import Config

    asyncio.run(set_webhook())

    config = Config()
    config.bind = [f"0.0.0.0:{os.getenv('PORT', 5000)}"]
    from hypercorn.asyncio import serve
    asyncio.run(serve(app, config))
