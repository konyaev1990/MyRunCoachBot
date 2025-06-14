import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Настройка логгирования
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

# Вопросы анкеты (оставьте ваши текущие вопросы)

# Обработчики команд (оставьте ваши текущие обработчики start, ask_question и др.)

# Webhook обработчик
@app.post(f'/{TOKEN}')
def telegram_webhook():
    try:
        update = Update.de_json(request.get_json(), application.bot)
        application.update_queue.put_nowait(update)
        return '', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return '', 500

@app.get('/')
def health_check():
    return 'Bot is running!', 200

async def main():
    await application.initialize()
    await application.bot.set_webhook(WEBHOOK_URL)
    await application.start()

if __name__ == '__main__':
    if os.getenv('ENV') == 'development':
        application.run_polling()
    else:
        # Production режим для Render
        port = int(os.getenv('PORT', 5000))
        
        from hypercorn.asyncio import serve
        from hypercorn.config import Config
        
        config = Config()
        config.bind = [f"0.0.0.0:{port}"]
        
        try:
            asyncio.run(main())
            asyncio.run(serve(app, config))
        except Exception as e:
            logger.error(f"Server error: {e}")
