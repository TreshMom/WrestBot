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
        [KeyboardButton("🎥 Видео")],
        [KeyboardButton("💳 Оплата")],
        [KeyboardButton("ℹ️ Информация о тренере")],
        [KeyboardButton("📞 Контакты")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def handle_message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🎥 Видео":
        await handle_video(update, context)
    elif text == "💳 Оплата":
        await handle_payment_info(update, context)
    elif text == "ℹ️ Информация о тренере":
        await handle_info(update, context)
    elif text == "📞 Контакты":
        await handle_contacts(update, context)


async def handle_payment_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    price = db.get_setting("price")
    period = db.get_setting("period")
    
    if db.is_user_paid(user_id):
        # Получаем дату окончания подписки
        subscription_end = db.get_user_subscription_end(user_id)
        try:
            end_date = datetime.strptime(subscription_end, "%Y-%m-%d %H:%M:%S")
            formatted_date = end_date.strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            formatted_date = "неизвестная дата"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"🔄 Продлить еще на {period} мес. за {price} руб", 
                    callback_data="init_payment"
                )
            ],
            [InlineKeyboardButton("🔙 Назад", callback_data="go_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"У вас уже есть подписка до *{formatted_date}*\n\n"
            f"Вы можете продлить её еще на {period} месяца",
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        return
    
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
    group_id = int(db.get_setting("chat_id"))
    now = datetime.now()
    
async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.now()

    with sqlite3.connect(db.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT data_end FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        data_end_str = row[0] if row else None

    try:
        current_end = datetime.strptime(data_end_str, "%Y-%m-%d %H:%M:%S") if data_end_str else None
    except ValueError:
        current_end = None

    if current_end and current_end > now:
        start_from = current_end
    else:
        start_from = now

    period = int(db.get_setting("period"))
    new_end = start_from + relativedelta(months=period)

    with sqlite3.connect(db.DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE users SET 
                is_paid = 1,
                payment_date = ?,
                data_end = ?
            WHERE user_id = ?
        """, (now.strftime("%Y-%m-%d %H:%M:%S"), new_end.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        conn.commit()

    await update.message.reply_text(
        f"✅ Оплата прошла успешно!\n"
        f"Ваша подписка активна до *{new_end.strftime('%d.%m.%Y')}*.\n"
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
            f"🎥 Cсылка на закрытый канал c видеоматериалом: {channel}",
            reply_markup=get_main_keyboard_user(),
        )
    else:
        await update.message.reply_text(
            "⚠️ Для доступа к видео необходимо оплатить подписку.\nНажмите кнопку '💳 Оплата'",
            reply_markup=get_main_keyboard_user(),
        )


#Функция для обработки заявок на вступление в группу
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

# Функция для проверки и удаления просроченных подписок
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

# Функция для отправки напоминаний о истечении подписки
async def send_subscription_reminders(context):
    """Отправляет напоминания пользователям за 10, 7, 4 и 1 день до истечения подписки"""
    now = datetime.now()
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    
    # Получаем всех пользователей с активной подпиской
    c.execute("SELECT user_id, data_end FROM users WHERE is_paid = 1")
    rows = c.fetchall()
    
    for user_id, date_end in rows:
        try:
            end_dt = datetime.strptime(date_end, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
            
        # Вычисляем количество дней до истечения
        days_left = (end_dt - now).days
        
        # Отправляем напоминания за 10, 7, 4 и 1 день
        if days_left in [10, 7, 4, 1] and days_left > 0:
            try:
                formatted_date = end_dt.strftime("%d.%m.%Y")
                price = db.get_setting("price")
                period = db.get_setting("period")
                
                # Создаем клавиатуру с кнопкой продления
                keyboard = [
                    [
                        InlineKeyboardButton(
                            f"🔄 Продлить на {period} мес. за {price} руб", 
                            callback_data="init_payment"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if days_left == 1:
                    message = (
                        f"⚠️ *Внимание!* Ваша подписка истекает завтра ({formatted_date})!\n\n"
                        f"Продлите подписку, чтобы не потерять доступ к материалам."
                    )
                else:
                    message = (
                        f"🔔 *Напоминание:* Ваша подписка истекает через {days_left} дней ({formatted_date})\n\n"
                        f"Не забудьте продлить подписку, чтобы продолжить обучение."
                    )
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                
                logger.info(f"Отправлено напоминание пользователю {user_id} за {days_left} дней до истечения подписки")
                
            except Exception as e:
                logger.error(f"Ошибка отправки напоминания пользователю {user_id}: {e}")
    
    conn.close()
