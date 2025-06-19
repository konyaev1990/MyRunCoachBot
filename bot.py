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
from datetime import datetime

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Questionnaire configuration
QUESTIONS = [
    {
        "text": "Когда Ваш старт? (например 20.06.2025)",
        "type": "input",
        "validate": lambda x: validate_date(x)
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
        "options": ["Нет", "Болят колени", "Болит надкостница", "Другое"]
    },
    {
        "text": "Сколько максимально километров пробегали за тренировку?",
        "type": "input",
        "validate": lambda x: x.isdigit() and 0 < int(x) <= 100
    },
    {
        "text": "За последние три месяца в каких соревнованиях принимали участие?",
        "type": "multi_input",
        "options": ["Не участвовал"]
    }
]

# Conversation states
QUESTION, CLARIFICATION = range(2)
user_data = {}

def validate_date(date_str):
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except ValueError:
        return False

def generate_prompt(answers):
    try:
        start_date = datetime.strptime(answers.get(QUESTIONS[0]["text"], "01.01.1900"), "%d.%m.%Y")
        days_left = (start_date - datetime.now()).days
    except (ValueError, TypeError):
        days_left = "неизвестно (проверьте формат даты)"

    prompt = f"""Составь подробную программу тренировок для подготовки к забегу на основе следующих данных:
    
Текущий уровень подготовки: {answers.get(QUESTIONS[2]["text"], "")}
Планируемая дистанция: {answers.get(QUESTIONS[1]["text"], "")}
До старта осталось: {days_left} дней
Доступное время на тренировки: {answers.get(QUESTIONS[5]["text"], "")}
Количество тренировок в неделю: {answers.get(QUESTIONS[3]["text"], "")}
Место тренировок: {answers.get(QUESTIONS[4]["text"], "")}
Максимальная дистанция на тренировке: {answers.get(QUESTIONS[7]["text"], "")} км
Ограничения по здоровью: {answers.get(QUESTIONS[6]["text"], "")}
Участие в соревнованиях: {answers.get(QUESTIONS[8]["text"], "")}

Программа должна включать:
1. Продолжительность подготовки по неделям
2. Типы тренировок (интервальные, темповые, длинные и т.д.)
3. Рекомендации по восстановлению
4. Советы по питанию и гидратации
5. Рекомендации по экипировке
6. План на последнюю неделю перед стартом

Ответ представь в формате Markdown с четкой структурой и заголовками."""
    
    return prompt

def generate_training_program(answers):
    try:
        prompt = generate_prompt(answers)
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        
        if not response.text:
            raise ValueError("Empty response from model")
            
        return response.text
    except Exception as e:
        logger.error(f"Error generating training program: {e}")
        return "⚠️ Произошла ошибка при генерации программы тренировок. Пожалуйста, попробуйте позже."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {}
    context.user_data.clear()
    
    await update.message.reply_text(
        "🏃‍♂️ Привет! Я помогу тебе подготовиться к забегу.\n"
        "Давай заполним анкету из 9 вопросов - это займет пару минут.\n"
        "После этого я составлю персонализированную программу тренировок!\n\n"
        "Если хочешь прервать заполнение анкеты, просто нажми /cancel",
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

    await update.message.reply_text(
        f"❓ Вопрос {current_index + 1}/{len(QUESTIONS)}:\n{question['text']}",
        reply_markup=reply_markup
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    answer = update.message.text.strip()
    current_question = context.user_data["current_question"]

    if context.user_data.get("awaiting_clarification"):
        if not answer:
            await update.message.reply_text("Пожалуйста, введите уточнение:")
            return CLARIFICATION
            
        user_data[user_id][current_question["text"]] = f"Другое: {answer}"
        context.user_data["awaiting_clarification"] = False
        await ask_question(update, context)
        return QUESTION

    if "options" in current_question and answer not in current_question["options"]:
        await update.message.reply_text("Пожалуйста, выберите вариант из предложенных:")
        return QUESTION

    if current_question.get("type") == "input":
        if "validate" in current_question and not current_question["validate"](answer):
            error_msg = {
                QUESTIONS[0]["text"]: "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ",
                QUESTIONS[7]["text"]: "Пожалуйста, введите число от 1 до 100"
            }.get(current_question["text"], "Некорректный ввод. Пожалуйста, попробуйте еще раз.")
            
            await update.message.reply_text(error_msg)
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
    await update.message.reply_text(
        "✅ Спасибо за ответы! Генерирую вашу программу...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    try:
        program = generate_training_program(user_data[user_id])
        chunks = [program[i:i+4000] for i in range(0, len(program), 4000)]
        
        for chunk in chunks:
            await update.message.reply_text(
                chunk,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
            
        await update.message.reply_text(
            "🏁 Удачных тренировок! Для новой программы нажми /start\n\n"
            "Рекомендую сохранить эту программу в тренировочный дневник."
        )
    except Exception as e:
        logger.error(f"Error sending program: {e}")
        await update.message.reply_text(
            "😕 Произошла ошибка. Пожалуйста, попробуйте позже."
        )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data:
        del user_data[user_id]
        
    await update.message.reply_text(
        "❌ Заполнение анкеты прервано. Все данные удалены.\n"
        "Если передумаешь - просто нажми /start",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def main():
    application = ApplicationBuilder() \
        .token(os.getenv("TELEGRAM_TOKEN")) \
        .build()
    
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
    application.add_handler(CommandHandler("cancel", cancel))
    
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
