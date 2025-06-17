import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Логирование
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем токен из переменных окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("No TELEGRAM_TOKEN provided in environment variables!")

# Создаем приложение Flask
app = Flask(__name__)

# Создаем Telegram Application
application = Application.builder().token(TOKEN).build()

# Простейшая команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я успешно работаю на Render через Webhook 🚀")

application.add_handler(CommandHandler("start", start))

# Webhook endpoint
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok"

# Healthcheck для Render
@app.route("/")
def healthcheck():
    return "Service is alive."

# Запуск приложения через Gunicorn будет происходить из Procfile
if __name__ == '__main__':
    app.run(port=10000)
