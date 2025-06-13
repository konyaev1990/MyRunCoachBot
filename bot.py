
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Вопросы бота (пример)
questions = [
    {"text": "Когда ваш старт? (Например: 20.09.2025)", "type": "input"},
    {"text": "Какая дистанция?", "options": ["5 км", "10 км", "21 км", "42 км"]},
    {"text": "Уровень подготовки?", "options": ["Новичок", "Опытный", "Профи"]},
    {"text": "Дней в неделю?", "options": ["2", "3", "5", "7"]}
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['answers'] = {}
    context.user_data['current_question'] = 0
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    index = context.user_data['current_question']
    if index >= len(questions):
        await update.message.reply_text("Спасибо! Программа будет сформирована ✅", reply_markup=ReplyKeyboardRemove())
        return

    q = questions[index]
    if 'options' in q:
        buttons = [[option] for option in q['options']]
        markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(q['text'], reply_markup=markup)
    else:
        await update.message.reply_text(q['text'], reply_markup=ReplyKeyboardRemove())

async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text
    index = context.user_data['current_question']
    question_text = questions[index]['text']
    context.user_data['answers'][question_text] = answer

    context.user_data['current_question'] += 1
    await ask_question(update, context)

if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))
    print("Бот запущен 🚀")
    app.run_polling()
