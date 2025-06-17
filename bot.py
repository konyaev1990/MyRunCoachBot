import asyncio
import logging
import os

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменные окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 10000))

# Хэндлер старт-команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я работаю через Render Webhook 🚀")

# Эхо-хэндлер
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

# Основной запуск
async def main():
    application = Application.builder().token(TOKEN).updater(None).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    await application.bot.set_webhook(url=f"{URL}/webhook")

    async def webhook_handler(request: Request) -> Response:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return Response()

    async def healthcheck(_: Request) -> PlainTextResponse:
        return PlainTextResponse("OK")

    app = Starlette(
        routes=[
            Route("/webhook", webhook_handler, methods=["POST"]),
            Route("/healthcheck", healthcheck, methods=["GET"]),
        ]
    )

    webserver = uvicorn.Server(
        config=uvicorn.Config(app=app, host="0.0.0.0", port=PORT, log_level="info")
    )

    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()

if __name__ == "__main__":
    asyncio.run(main())
