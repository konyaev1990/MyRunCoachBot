
import os
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("BOT_TOKEN")

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

user_states = {}

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {"answers": {}, "current_question": 0, "awaiting_custom_input": False}
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states[user_id]
    index = state["current_question"]
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
    user_id = update.effective_user.id
    state = user_states[user_id]
    index = state["current_question"]
    q = questions[index]
    answer = update.message.text

    state['answers'][q['text']] = answer

    if q['text'] == "Есть ли ограничения по здоровью или травмы?" and answer == "Другое":
        state['awaiting_custom_input'] = True
        await update.message.reply_text("Уточните, пожалуйста:")
        return

    if state.get('awaiting_custom_input'):
        state['answers']['Уточнение по травме'] = answer
        state['awaiting_custom_input'] = False

    state['current_question'] += 1
    await ask_question(update, context)

async def generate_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_states[user_id]['answers']

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

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Webhook running!", 200

if __name__ == "__main__":
    application.run_polling()
