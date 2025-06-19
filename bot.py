import logging
import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from dotenv import load_dotenv
import google.generativeai as genai

# Загрузка переменных окружения
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Вопросы анкеты
QUESTIONS = [
    {
        "text": "Когда Ваш старт? (например 20.06.2025)",
        "type": "input"
    },
    {
        "text": "Какая дистанция?",
        "options": ["800–3000 м", "3–10 км", "21 км", "42 км"]
    },
    {
        "text": "Ваш уровень подготовки?",
        "options": ["Новичок", "Любитель", "Опытный"]
    },
    {
        "text": "Сколько дней в неделю планируете бегать?",
        "options": ["1", "3", "5", "7"]
    },
    {
        "text": "Где будут проходить тренировки?",
        "options": ["Лес", "Парк", "Стадион", "Беговая дорожка"]
    },
    {
        "text": "Сколько времени готовы тратить на тренировку?",
        "options": ["до 45 мин", "45–60 мин", "60–90 мин"]
    },
    {
        "text": "Есть ли ограничения по здоровью или травмы?",
        "options": ["Болят колени", "Болит надкостница", "Другое"]
    },
    {
        "text": "Сколько максимально километров пробегали за тренировку?",
        "type": "input"
    },
    {
        "text": "За последние три месяца в каких соревнованиях принимали участие? (введите дистанцию и результат или нажмите 'Не участвовал')",
        "type": "multi_input",
        "options": ["Не участвовал"]
    }
]

QUESTION, CLARIFICATION = range(2)
user_data = {}

def generate_prompt(answers):
    parts = [f"{q['text']} {answers.get(q['text'], '')}" for q in QUESTIONS]
    return """Составь беговую программу на основе следующих ответов:
""" + "\n".join(parts) + """
"""

def generate_training_program(answers):
    prompt = generate_prompt(answers)
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text if hasattr(response, "text") else str(response)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я помогу составить программу тренировок. Давайте заполним анкету.",
        reply_markup=ReplyKeyboardRemove()
    )
    await ask_question(update, context)
    return QUESTION

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_index = context.user_data.get("current_index", -1) + 1
    if current_index >= len(QUESTIONS):
        return await finish_questionnaire(update, context)

    question = QUESTIONS[current_index]
    context.user_data["current_index"] = current_index
    context.user_data["current_question"] = question
    reply_markup = None
    if "options" in question:
        buttons = [[KeyboardButton(option)] for option in question["options"]]
        reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(question["text"], reply_markup=reply_markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answer = update.message.text
    current_question = context.user_data["current_question"]

    if context.user_data.get("awaiting_clarification"):
        user_data[user_id][current_question["text"]] = f"Другое: {answer}"
        context.user_data["awaiting_clarification"] = False
        await ask_question(update, context)
        return QUESTION

    if "options" in current_question and answer not in current_question["options"]:
        await update.message.reply_text("Пожалуйста, выберите вариант из предложенных:")
        return QUESTION

    if answer == "Другое" and "options" in current_question:
        context.user_data["awaiting_clarification"] = True
        await update.message.reply_text("Пожалуйста, уточните:")
        return CLARIFICATION

    user_data[user_id][current_question["text"]] = answer
    await ask_question(update, context)
    return QUESTION

async def finish_questionnaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    program = generate_training_program(user_data[user_id])
    await update.message.reply_text(
        program,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    await update.message.reply_text(
        "Спасибо за заполнение анкеты! Удачных тренировок! 💪\nДля новой анкеты нажмите /start"
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
    await update.message.reply_text(
        "Анкета отменена. Чтобы начать заново, нажмите /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            CLARIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    logger.info("Бот запущен")
    application.run_polling()

if __name__ == '__main__':
    main()
