import os
import logging
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import asyncio

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv('TOKEN')
WEBHOOK_URL = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"

# Инициализация приложений
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ... (остальные функции остаются без изменений) ...

# Webhook обработчик
@app.post(f'/{TOKEN}')
async def telegram_webhook():
    json_data = request.get_json()
    update = Update.de_json(json_data, application.bot)
    await application.update_queue.put(update)
    return '', 200

@app.get('/')
def health_check():
    return 'Bot is running!', 200

async def main():
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.start()

if __name__ == '__main__':
    # Для локальной разработки
    if os.getenv('ENV') == 'development':
        application.run_polling()
    else:
        # Для продакшена
        port = int(os.getenv('PORT', 5000))
        config = {
            'bind': f'0.0.0.0:{port}',
            'worker_class': 'asyncio',
        }
        from hypercorn.asyncio import serve
        from hypercorn.config import Config
        
        asyncio.run(main())
        serve(app, Config.from_mapping(config))
