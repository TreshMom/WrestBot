import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import sqlite3
from datetime import datetime, timedelta
import requests
import json
import time
from tinkoff.invest import Client
from tinkoff.invest.utils import now

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
PRIVATE_CHANNEL = os.getenv('PRIVATE_CHANNEL')

# Настройки Тинькофф API
TINKOFF_TOKEN = os.getenv('TINKOFF_TOKEN')  # Получите в личном кабинете Тинькофф
TINKOFF_ACCOUNT = os.getenv('TINKOFF_ACCOUNT')  # Номер вашего счета
SUBSCRIPTION_PRICE = os.getenv('SUBSCRIPTION_PRICE') # Цена в рублях

def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("💳 Оплата")],
        [KeyboardButton("📞 Контакты")],
        [KeyboardButton("🎥 Видео")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  is_paid BOOLEAN,
                  payment_date TEXT,
                  payment_id TEXT)''')
    conn.commit()
    conn.close()

def is_user_paid(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT is_paid FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else False

def generate_payment_id():
    """Генерирует уникальный идентификатор платежа"""
    return f"PAY_{int(time.time())}_{os.urandom(4).hex()}"

def check_payment(payment_id):
    """Проверяет статус платежа через API Тинькофф"""
    try:
        with Client(TINKOFF_TOKEN) as client:
            # Получаем операции по счету
            operations = client.operations.get_operations(
                account_id=TINKOFF_ACCOUNT,
                from_=now() - timedelta(days=1),
                to=now()
            )

            # Ищем операцию с нужным комментарием
            for operation in operations.operations:
                if operation.description == payment_id and operation.payment >= SUBSCRIPTION_PRICE:
                    return True
            
            return False
    except Exception as e:
        logger.error(f"Error checking payment: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, is_paid) VALUES (?, ?, ?)",
              (user_id, username, False))
    conn.commit()
    conn.close()

    with open('hello.mp4', 'rb') as video:
        await update.message.reply_video(
            video=video,
            caption="☝️Что тебя ждем на канале? В этом коротком видео вся информация",
            reply_markup=get_main_keyboard()
        )

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки оплаты"""
    user_id = update.effective_user.id
    payment_id = generate_payment_id()
    
    # Сохраняем payment_id в базе данных
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET payment_id = ? WHERE user_id = ?", (payment_id, user_id))
    conn.commit()
    conn.close()

    payment_message = f"""
💳 Оплата подписки

Сумма: {SUBSCRIPTION_PRICE} руб.
Номер счета: {TINKOFF_ACCOUNT}
Комментарий к платежу: {payment_id}

⚠️ Важно: обязательно укажите комментарий к платежу!
После оплаты нажмите кнопку "Проверить оплату"
    """
    
    keyboard = [[InlineKeyboardButton("Проверить оплату", callback_data=f"check_{payment_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        payment_message,
        reply_markup=reply_markup
    )

async def handle_payment_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик проверки оплаты"""
    query = update.callback_query
    await query.answer()
    
    payment_id = query.data.split("_")[1]
    user_id = update.effective_user.id
    
    if check_payment(payment_id):
        # Обновляем статус оплаты
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_paid = ?, payment_date = ? WHERE user_id = ?",
                  (True, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        conn.close()

        # Создаем приглашение в канал
        try:
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=PRIVATE_CHANNEL,
                member_limit=1,
                expire_date=int((datetime.now() + timedelta(days=1)).timestamp())
            )
            await query.message.reply_text(
                f"✅ Оплата подтверждена!\n\n"
                f"🎥 Вот ваша ссылка для вступления в закрытый канал:\n"
                f"{invite_link.invite_link}\n\n"
                f"⚠️ Ссылка действительна 24 часа",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            logger.error(f"Error creating invite link: {e}")
            await query.message.reply_text(
                "✅ Оплата подтверждена!\n"
                "Свяжитесь с администратором для получения доступа к каналу.",
                reply_markup=get_main_keyboard()
            )
    else:
        await query.message.reply_text(
            "❌ Оплата не найдена. Пожалуйста, проверьте:\n"
            "1. Правильность указанного комментария к платежу\n"
            "2. Прошло ли достаточно времени для обработки платежа\n\n"
            "Попробуйте проверить оплату через несколько минут.",
            reply_markup=get_main_keyboard()
        )

async def handle_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📞 Свяжитесь с администратором: {ADMIN_USERNAME}",
        reply_markup=get_main_keyboard()
    )

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if is_user_paid(user_id):
        await update.message.reply_text(
            f"🎥 Вот ссылка на закрытый канал: {PRIVATE_CHANNEL}",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "⚠️ Для доступа к видео необходимо оплатить подписку.\nНажмите кнопку '💳 Оплата'",
            reply_markup=get_main_keyboard()
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💳 Оплата":
        await handle_payment(update, context)
    elif text == "📞 Контакты":
        await handle_contacts(update, context)
    elif text == "🎥 Видео":
        await handle_video(update, context)

def main():
    init_db()
    
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_payment_check, pattern="^check_"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 