import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from flask import Flask, request

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

# Flask app для webhook
app = Flask(__name__)

# Telegram Bot token из переменной окружения
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Создаём Telegram приложение
telegram_app = ApplicationBuilder().token(TOKEN).build()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = {}
    context.user_data['current_question'] = 0
    await ask_question(update, context)

# Задаём вопросы
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

# Обработка ответов
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

# Генерация программы на основе ответов
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

# Регистрируем обработчики
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

# Webhook обработчик
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    await telegram_app.process_update(Update.de_json(data, telegram_app.bot))
    return "ok"

# Проверка на главной странице
@app.route("/", methods=["GET"])
def home():
    return "MyRunCoachBot is alive!"

