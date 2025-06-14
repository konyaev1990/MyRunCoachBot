import os
import logging
from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set in environment variables")

# Создаем Flask приложение
app = Flask(__name__)

# Создаем Telegram Application (PTB)
application = Application.builder().token(TOKEN).build()

# Вопросы анкеты
questions = [
    {"text": "Когда Ваш старт? (например: 20.06.2025)", "type": "input"},
    {"text": "Какая дистанция?", "options": ["800–3000 м", "3–10 км", "21 км", "42 км"]},
    {"text": "Ваш уровень подготовки?", "options": ["Новичок", "Любитель", "Опытный"]},
    {"text": "Сколько дней в неделю планируете бегать?", "options": ["1", "3", "5", "7"]},
    {"text": "Где будут проходить тренировки?", "options": ["Парк", "Стадион", "Лес"]},
    {"text": "Сколько времени готовы тратить на тренировку?", "options": ["45 мин", "45–60 мин", "60–90 мин"]},
    {"text": "Есть ли ограничения по здоровью или травмы?", "options": ["Колени", "Надкостница", "Другое"]},
    {"text": "Сколько максимально пробегали за тренировку?", "type": "input"},
    {"text": "Какие соревнования бегали последнее время? (введите дистанцию и результат или нажмите 'Не участвовал')", "type": "multi_input", "options": ["Не участвовал"]}
]

# Обработчики команд (остаются без изменений)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = {}
    context.user_data['current_question'] = 0
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['current_question']
    if index >= len(questions):
        await generate_program(update, context)
        return

    q = questions[index]
    if 'options' in q:
        buttons = [[KeyboardButton(option)] for option in q['options']]
        markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(q['text'], reply_markup=markup)
    else:
        await update.message.reply_text(q['text'], reply_markup=ReplyKeyboardRemove())

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data.get('current_question', 0)
    q = questions[index]
    answer = update.message.text

    context.user_data['answers'][q['text']] = answer

    if q['text'] == "Есть ли ограничения по здоровью или травмы?" and answer == "Другое":
        context.user_data['awaiting_custom_input'] = True
        await update.message.reply_text("Уточните, пожалуйста:")
        return

    if context.user_data.get('awaiting_custom_input'):
        context.user_data['answers']['Уточнение по травме'] = answer
        context.user_data['awaiting_custom_input'] = False

    context.user_data['current_question'] += 1
    await ask_question(update, context)

async def generate_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data['answers']
    result = "\U0001F3C1 Ваша программа тренировок:\n\n"
    for key, value in data.items():
        result += f"{key}: {value}\n"

    result += "\n\U0001F4C5 Примерная структура недели:\n"
    dist = data.get("Какая дистанция?")
    if dist == "42 км":
        result += "- Темповый бег\n- Интервалы\n- Долгий бег\n- Восстановление"
    elif dist == "21 км":
        result += "- Бег 3 раза в неделю\n- Кардио\n- Растяжка"
    else:
        result += "- Бег 3–5 раз в неделю\n- Силовые\n- Интервалы"

    await update.message.reply_text(result, reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("Спасибо! Удачи на тренировках! \U0001F4AA")

# Подключаем handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

# Webhook маршрут
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)
    return "OK"

@app.route("/")
def index():
    return "Bot is running!"

async def set_webhook():
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    await application.bot.set_webhook(webhook_url)

if __name__ == '__main__':
    # Для локальной разработки
    if os.environ.get('ENV') == 'development':
        application.run_polling()
    else:
        # Для продакшена на Render
        port = int(os.environ.get("PORT", 5000))
        # Запускаем Flask синхронно
        app.run(host="0.0.0.0", port=port)
