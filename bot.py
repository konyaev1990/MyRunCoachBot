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

# Анкета
QUESTIONS = [
    {"text": "Когда Ваш старт? (например: 20.06.2025)", "type": "input"},
    {"text": "Какая дистанция?", "options": ["800–3000 м", "3–10 км", "21 км", "42 км"]},
    {"text": "Ваш уровень подготовки?", "options": ["Новичок", "Любитель", "Опытный"]},
    {"text": "Сколько дней в неделю планируете бегать?", "options": ["1", "3", "5", "7"]},
    {"text": "Где будут проходить тренировки?", "options": ["Парк", "Стадион", "Лес"]},
    {"text": "Сколько времени готовы тратить на тренировку?", "options": ["45 мин", "45–60 мин", "60–90 мин"]},
    {"text": "Есть ли ограничения по здоровью или травмы?", "options": ["Колени", "Надкостница", "Другое"]},
    {"text": "Сколько максимально пробегали за тренировку?", "type": "input"},
    {"text": "Какие соревнования бегали последнее время? (введите дистанцию и результат или нажмите 'Не участвовал')", 
     "type": "multi_input", "options": ["Не участвовал"]}
]

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    context.user_data.clear()
    context.user_data['current_question'] = 0
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Задаем следующий вопрос"""
    index = context.user_data.get('current_question', 0)
    
    if index >= len(QUESTIONS):
        await generate_program(update, context)
        return
    
    question = QUESTIONS[index]
    
    if 'options' in question:
        keyboard = [[KeyboardButton(option)] for option in question['options']]
        await update.message.reply_text(
            question['text'],
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(question['text'], reply_markup=ReplyKeyboardRemove())

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов пользователя"""
    index = context.user_data.get('current_question', 0)
    question = QUESTIONS[index]
    answer = update.message.text

    context.user_data['answers'][question['text']] = answer

    if question['text'] == "Есть ли ограничения по здоровью или травмы?" and answer == "Другое":
        context.user_data['awaiting_custom_input'] = True
        await update.message.reply_text("Уточните, пожалуйста:")
        return

    if context.user_data.get('awaiting_custom_input'):
        context.user_data['answers']['Уточнение по травме'] = answer
        context.user_data['awaiting_custom_input'] = False

    context.user_data['current_question'] += 1
    await ask_question(update, context)

async def generate_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация программы тренировок"""
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

# Подключаем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

# Webhook обработчик
@app.post(f'/{TOKEN}')
async def telegram_webhook():
    """Асинхронный обработчик вебхука"""
    json_data = await request.get_json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return '', 200

@app.get('/')
def health_check():
    """Проверка работоспособности"""
    return 'Bot is running!', 200

# Инициализация вебхука
async def set_webhook():
    """Установка вебхука"""
    await application.bot.set_webhook(WEBHOOK_URL)

if __name__ == '__main__':
    # Для локальной разработки
    if os.getenv('ENV') == 'development':
        application.run_polling()
    else:
        # Для продакшена на Render
        port = int(os.getenv('PORT', 5000))
        
        # Запускаем Flask с поддержкой асинхронности
        from hypercorn.asyncio import serve
        from hypercorn.config import Config
        
        config = Config()
        config.bind = [f"0.0.0.0:{port}"]
        
        async def run():
            await set_webhook()
            await serve(app, config)
        
        asyncio.run(run())
