from telegram import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    PreCheckoutQuery
)
from telegram.ext import ContextTypes
import sqlite3
import db

from dateutil.relativedelta import relativedelta
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, is_paid) VALUES (?, ?, ?)",
        (user_id, username, False),
    )
    conn.commit()
    conn.close()

    with open("hello.mp4", "rb") as video:
        await update.message.reply_video(
            video=video,
            caption="☝️Что тебя ждет на канале?\n В этом коротком видео вся информация \n",
            reply_markup=get_main_keyboard_user(),
        )


def get_main_keyboard_user():
    """Создает основную клавиатуру"""
    keyboard = [
        [KeyboardButton("💳 Оплата")],
        [KeyboardButton("📞 Контакты")],
        [KeyboardButton("🎥 Видео")],
        [KeyboardButton("ℹ️ Информация о тренере")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def handle_message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💳 Оплата":
        await handle_payment_info(update, context)
    elif text == "📞 Контакты":
        await handle_contacts(update, context)
    elif text == "🎥 Видео":
        await handle_video(update, context)
    elif text == "ℹ️ Информация о тренере":
        await handle_info(update, context)


async def handle_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    """
    if db.is_user_paid(user_id):
        await update.message.reply_text(
            "Вы уже оплатили подписку на ближайший период.",
            reply_markup=get_main_keyboard_user(),
        )
        return
    """
    price = db.get_setting("price")
    period = db.get_setting("period")
    text = db.get_setting("text_payment")
    keyboard = [
        [
            InlineKeyboardButton(
                f"💳 Оплатить {price} руб", callback_data="init_payment"
            )
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="go_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            text
            + "\n" +
            f"Стоимость подписки: *{price} руб* за {period} месяца\n\n"
            "Нажмите кнопку ниже, чтобы перейти к оплате",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


async def init_payment_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки оплаты"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    provide_token = db.get_setting("bank_token") 
    price = int(db.get_setting("price")) * 100  # Telegram требует цену в копейках
    period = int(db.get_setting("period"))

    await context.bot.send_invoice(
        chat_id=user_id,
        title="Подписка на курс",
        description=f"Доступ к каналу на {period} мес.",
        payload="payment-subscription",  # Используй для идентификации
        provider_token=provide_token,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=price)],
        start_parameter="subscription-start",
        need_name=False,
        need_email=False,
        need_phone_number=False,
    )

async def handle_precheckout_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: PreCheckoutQuery = update.pre_checkout_query
    if query.invoice_payload != "payment-subscription":
        await query.answer(ok=False, error_message="Что-то пошло не так при проверке платежа.")
    else:
        await query.answer(ok=True)

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now()
    data_end_str = db.get_setting("data_end")
    try:
        current_end = datetime.strptime(data_end_str, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        current_end = None
    else:
        now = datetime.now()

    if current_end and current_end > now:
        start_from = current_end
    else:
        start_from = now

    period = int(db.get_setting("period"))
    new_end = start_from + relativedelta(months=period)
    
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        UPDATE users SET 
            is_paid = 1,
            payment_date = ?,
            data_end = ?
        WHERE user_id = ?
    """, (now.strftime("%Y-%m-%d %H:%M:%S"), new_end.strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Оплата прошла успешно!\n"
        f"Ваша подписка активна до *{new_end.strftime('%d.%m.%Y')}*"
        f"Нажмите на вкладку '🎥Видео'.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard_user(),
    )

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "Вы вернулись в главное меню", reply_markup=get_main_keyboard_user()
    )

async def handle_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contacts = db.get_setting("support_concat") or "Контакты не указаны"
    temp ="Связь по вопросам: "
    await update.message.reply_text(temp + contacts, reply_markup=get_main_keyboard_user())


async def handle_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info = db.get_setting("description_coach") or "Информация не указана"
    await update.message.reply_text(info, reply_markup=get_main_keyboard_user())


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    channel = db.get_setting("link_chanal")
    if db.is_user_paid(user_id):
        await update.message.reply_text(
            f"🎥 Вот ссылка на закрытый канал: {channel}",
            reply_markup=get_main_keyboard_user(),
        )
    else:
        await update.message.reply_text(
            "⚠️ Для доступа к видео необходимо оплатить подписку.\nНажмите кнопку '💳 Оплата'",
            reply_markup=get_main_keyboard_user(),
        )


# Новый обработчик заявок на вступление в группу
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    user_id = user.id
    username = user.username

    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT is_paid FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()

    if row and row[0]:  # Если пользователь оплатил
        try:
            await context.bot.approve_chat_join_request(
                chat_id=update.chat_join_request.chat.id, user_id=user_id
            )
            await context.bot.send_message(
                chat_id=user_id,
                text="✅ Ваша заявка принята, добро пожаловать в группу!",
            )
            logger.info(
                f"Пользователь @{username} ({user_id}) принят в группу автоматически."
            )
        except Exception as e:
            logger.error(f"Ошибка при принятии заявки: {e}")
    else:
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ Вы ещё не оплатили подписку. Пожалуйста, оплатите, чтобы получить доступ.",
        )


async def check_and_remove_expired_subscriptions(context):
    group_id = int(db.get_setting("chat_id"))
    now = datetime.now()
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, data_end FROM users WHERE is_paid = 1")
    rows = c.fetchall()
    for user_id, date_end in rows:
        try:
            end_dt = datetime.strptime(date_end, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if now > end_dt:
            try:
                await context.bot.ban_chat_member(group_id, user_id)
                await context.bot.unban_chat_member(group_id, user_id)
            except Exception as e:
                logger.error(f"Ошибка удаления пользователя {user_id}: {e}")
            # Обновить пользователя в базе
            c.execute(
                "UPDATE users SET is_paid = 0, payment_date = NULL, data_end = NULL WHERE user_id = ?",
                (user_id,),
            )
            conn.commit()
    conn.close()
