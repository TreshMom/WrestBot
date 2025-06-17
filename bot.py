import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ChatJoinRequestHandler
)
import sqlite3
from datetime import datetime, timedelta
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
SUBSCRIPTION_PRICE = int(os.getenv('SUBSCRIPTION_PRICE', '2000'))  # Цена в рублях


def get_main_keyboard():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("💳 Оплата")],
        [KeyboardButton("📞 Контакты")],
        [KeyboardButton("🎥 Видео")],
        [KeyboardButton("ℹ️ Информация о тренере")]
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
            operations = client.operations.get_operations(
                account_id=TINKOFF_ACCOUNT,
                from_=now() - timedelta(days=1),
                to=now()
            )

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
            caption="☝️Что тебя ждет на канале? В этом коротком видео вся информация \n Стоимость подписки: 2000 рублей за 3 месяца",
            reply_markup=get_main_keyboard()
        )


async def handle_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Оплатить 2000 руб", callback_data="init_payment")],
        [InlineKeyboardButton("🔙 Назад", callback_data="go_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            "🥋 *Курс борьбы*\n\n"
            "🔥 Доступ к эксклюзивным видео, техникам и тренировкам\n"
            "💰 Стоимость подписки: *2000 руб* за 3 месяца\n\n"
            "Нажмите кнопку ниже, чтобы перейти к оплате",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )


async def init_payment_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки оплаты"""
    user_id = update.effective_user.id

    # Проверяем, есть ли уже оплата
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT is_paid FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if row and row[0]:  # если is_paid = 1
        await update.callback_query.answer()  # закрываем лоадер у кнопки
        await update.callback_query.message.reply_text(
            "✅ Подписка на текущий период уже оплачена.",
            reply_markup=get_main_keyboard()
        )
        conn.close()
        return

    # Если не оплачено — продолжаем процесс оплаты
    payment_id = generate_payment_id()
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

    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        payment_message,
        reply_markup=reply_markup
    )


async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Вы вернулись в главное меню", reply_markup=get_main_keyboard())


async def handle_payment_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик проверки оплаты"""
    query = update.callback_query
    await query.answer()
    
    payment_id = query.data.split("_", 1)[1]
    user_id = update.effective_user.id
    
    if check_payment(payment_id):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_paid = ?, payment_date = ? WHERE user_id = ?",
                  (True, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()
        conn.close()

        await query.message.reply_text(
            "✅ Оплата подтверждена! Теперь вы можете отправить заявку на вступление в группу.",
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


async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Максим Александрович, четырех кратный победитель кубка галактики, трехкратный призер дворовых игр без правил",
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
        await handle_payment_info(update, context)
    elif text == "📞 Контакты":
        await handle_contacts(update, context)
    elif text == "🎥 Видео":
        await handle_video(update, context)
    elif text == "ℹ️ Информация о тренере":
        await handle_info(update, context)


# Новый обработчик заявок на вступление в группу
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    user_id = user.id
    username = user.username

    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT is_paid FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if row and row[0]:  # Если пользователь оплатил
        try:
            await context.bot.approve_chat_join_request(
                chat_id=update.chat_join_request.chat.id,
                user_id=user_id
            )
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Ваша заявка принята, добро пожаловать в группу!"
            )
            logger.info(f"Пользователь @{username} ({user_id}) принят в группу автоматически.")
        except Exception as e:
            logger.error(f"Ошибка при принятии заявки: {e}")
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Вы ещё не оплатили подписку. Пожалуйста, оплатите, чтобы получить доступ."
        )


def main():
    init_db()
    
    application = Application.builder().token(TOKEN).build()

    # Команды и сообщения
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработка callback кнопок
    application.add_handler(CallbackQueryHandler(handle_payment_check, pattern="^check_"))
    application.add_handler(CallbackQueryHandler(init_payment_process, pattern="^init_payment$"))
    application.add_handler(CallbackQueryHandler(handle_back, pattern="^go_back$"))

    # Обработчик заявок на вступление в группу
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
