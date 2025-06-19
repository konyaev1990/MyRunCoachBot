import logging
import os
import sys
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

try:
    from dotenv import load_dotenv
except ImportError:
    print("[ERROR] Установи dotenv: pip install python-dotenv")
    sys.exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("[ERROR] Установи Gemini SDK: pip install google-generativeai")
    sys.exit(1)

# Загрузка ключей
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not GEMINI_API_KEY or not TELEGRAM_TOKEN:
    print("[ERROR] Убедись, что установлены переменные GEMINI_API_KEY и TELEGRAM_TOKEN")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Вопросы анкеты
QUESTIONS = [
    {"text": "Когда Ваш старт? (например 20.06.2025)", "type": "input"},
    {"text": "Какая дистанция?", "options": ["800–3000 м", "3–10 км", "21 км", "42 км"]},
    {"text": "Ваш уровень подготовки?", "options": ["Новичок", "Любитель", "Опытный"]},
    {"text": "Сколько дней в неделю планируете бегать?", "options": ["1", "3", "5", "7"]},
    {"text": "Где будут проходить тренировки?", "options": ["Лес", "Парк", "Стадион", "Беговая дорожка"]},
    {"text": "Сколько времени готовы тратить на тренировку?", "options": ["до 45 мин", "45–60 мин", "60–90 мин"]},
    {"text": "Есть ли ограничения по здоровью или травмы?", "options": ["Болят колени", "Болит надкостница", "Другое"]},
    {"text": "Сколько максимально километров пробегали за тренировку?", "type": "input"},
    {"text": "В каких соревнованиях участвовали за последние 3 месяца? (или 'Не участвовал')", "type": "multi_input"}
]

QUESTION, CLARIFICATION = range(2)
user_data = {}

def generate_prompt(answers):
    parts = [f"{q['text']} {answers.get(q['text'], '')}" for q in QUESTIONS]
    return "Составь беговую программу на основе следующих ответов:\n\n" + "\n".join(parts)

def generate_training_program(answers):
    prompt = generate_prompt(answers)
    try:
        model = genai.GenerativeModel("models/gemini-2.0-flash")
        response = model.generate_content(prompt)
        return response.text if hasattr(response, "text") else str(response)
    except Exception as e:
        logger.error(f"[Gemini Error] {e}")
        return "⚠️ Не удалось получить ответ от Gemini. Попробуйте позже."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    context.user_data.clear()
    await update.message.reply_text("Привет! Давайте начнем анкету 💬", reply_markup=ReplyKeyboardRemove())
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
    question = context.user_data.get("current_question")

    if context.user_data.get("awaiting_clarification"):
        user_data[user_id][question["text"]] = f"Другое: {answer}"
        context.user_data["awaiting_clarification"] = False
        return await ask_question(update, context)

    if "options" in question and answer not in question["options"]:
        await update.message.reply_text("Выберите из предложенных вариантов.")
        return QUESTION

    if answer == "Другое" and "options" in question:
        context.user_data["awaiting_clarification"] = True
        await update.message.reply_text("Пожалуйста, уточните:")
        return CLARIFICATION

    user_data[user_id][question["text"]] = answer
    return await ask_question(update, context)

async def finish_questionnaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answers = user_data.get(user_id, {})
    if not answers:
        await update.message.reply_text("Ошибка: нет данных для генерации.")
        return ConversationHandler.END

    program = generate_training_program(answers)
    await update.message.reply_text(program, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    await update.message.reply_text("🏁 Чтобы пройти снова, введите /start")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data.pop(user_id, None)
    await update.message.reply_text("❌ Анкета отменена. Введите /start для начала.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            CLARIFICATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
    application.add_handler(conv_handler)
    logger.info("✅ Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()
