import sqlite3
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import os 
import db
import user
from telegram.ext import ConversationHandler

BACK_BUTTON = "⬅️ Назад"

def get_back_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True, one_time_keyboard=True)


def get_main_keyboard_admin():
    """Создает основную клавиатуру"""
    keyboard = [
        #[KeyboardButton("🎥 Добавить видео")],
        [KeyboardButton("💳 Изменить цену на подписку")],
        [KeyboardButton("📞 Изменить период подписки")],
        [KeyboardButton("🎥 Изменить контакты")],
        [KeyboardButton("ℹ️ Изменить информацию о тренере")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_ids = (db.get_setting('admin_usernames') or '').split(',')
    admin_ids = [int(x.strip()) for x in admin_ids if x.strip().isdigit()]
    user_id = update.effective_user.id
    if user_id not in admin_ids:
        await update.message.reply_text('Нет доступа')
        return
    await update.message.reply_text(
        "Вы вошли как администратор",
        reply_markup=get_main_keyboard_admin()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_ids = (db.get_setting('admin_usernames') or '').split(',')
        admin_ids = [int(x.strip()) for x in admin_ids if x.strip().isdigit()]

        user_id = update.effective_user.id
        if user_id in admin_ids:
            await handle_message_admin(update, context)
        else:
            await handle_message_user(update, context)

async def handle_message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💳 Оплата":
        await user.handle_payment_info(update, context)
    elif text == "📞 Контакты":
        await user.handle_contacts(update, context)
    elif text == "🎥 Видео":
        await user.handle_video(update, context)
    elif text == "ℹ️ Информация о тренере":
        await user.handle_info(update, context)

async def handle_message_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💳 Оплата":
        await user.handle_payment_info(update, context)
    elif text == "📞 Контакты":
        await user.handle_contacts(update, context)
    elif text == "🎥 Видео":
        await user.handle_video(update, context)
    elif text == "ℹ️ Информация о тренере":
        await user.handle_info(update, context)
    elif text == "🎥 Добавить видео":
        await handle_add_video(update, context)
    elif text == "💳 Изменить цену на подписку":
        await handle_change_price(update, context)
    elif text == "📞 Изменить период подписки":
        await handle_change_period(update, context)
    elif text == "ℹ️ Изменить информацию о тренере":
        await handle_change_info(update, context) 
    elif text == "🎥 Изменить контакты":
        await handle_change_contacts(update, context)
    elif text == "⬅️ Назад":
        await handle_back_to_admin_menu(update, context)



ADD_VIDEO_TOPIC, ADD_VIDEO_TITLE, ADD_VIDEO_FILE, ADD_VIDEO_DESCRIPTION = range(4)
CHANGE_PRICE, CHANGE_PERIOD, CHANGE_CONTACTS, CHANGE_INFO = range(3, 7)

def get_topics_keyboard():
    topics = db.get_topics_from_settings()
    keyboard = [[KeyboardButton(topic)] for topic in topics]
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

async def handle_add_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите топик для видео:", reply_markup=get_topics_keyboard())
    return ADD_VIDEO_TOPIC

async def add_video_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_BUTTON:
        await update.message.reply_text("Главное меню администратора", reply_markup=get_main_keyboard_admin())
        return ConversationHandler.END
    context.user_data['video_topic'] = update.message.text
    await update.message.reply_text("Введите название видео:", reply_markup=get_back_keyboard())
    return ADD_VIDEO_TITLE

async def add_video_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_BUTTON:
        await update.message.reply_text("Выберите топик для видео:", reply_markup=get_topics_keyboard())
        return ADD_VIDEO_TOPIC
    context.user_data['video_title'] = update.message.text
    await update.message.reply_text("Отправьте видеофайл:", reply_markup=get_back_keyboard())
    return ADD_VIDEO_FILE

async def add_video_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_BUTTON:
        await update.message.reply_text("Введите название видео:", reply_markup=get_back_keyboard())
        return ADD_VIDEO_TITLE
    file = update.message.video or update.message.document
    if not file:
        await update.message.reply_text("Пожалуйста, отправьте видеофайл или нажмите 'Назад'.", reply_markup=get_back_keyboard())
        return ADD_VIDEO_FILE
    os.makedirs("videos", exist_ok=True)
    file_path = f"videos/{file.file_id}.mp4"
    tg_file = await file.get_file()
    await tg_file.download_to_drive(file_path)
    context.user_data['video_path'] = file_path
    await update.message.reply_text("Введите описание видео:", reply_markup=get_back_keyboard())
    return ADD_VIDEO_DESCRIPTION


async def track_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.forum_topic_created:
        topic = update.message.forum_topic_created
        await update.message.reply_text(f"Создан новый топик: {topic.name}")


async def add_video_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == BACK_BUTTON:
        await update.message.reply_text("Отправьте видеофайл:", reply_markup=get_back_keyboard())
        return ADD_VIDEO_FILE
    context.user_data['video_description'] = update.message.text
    # Получить chat_id группы и id топика (message_thread_id) по названию топика
    group_id = int(db.get_setting('chat_id'))  # group_id должен быть сохранён в settings
    topic_name = context.user_data['video_topic']
    # Получить список топиков через Bot API
    forum_topics = await update.get_bot().get_forum_topic_list(chat_id=group_id)
    topic_id = None
    for topic in forum_topics.topics:
        if topic.name == topic_name:
            topic_id = topic.message_thread_id
            break
    if not topic_id:
        await update.message.reply_text("Не найден топик с таким названием в группе.")
        return ConversationHandler.END
    # Отправить видео в нужный топик
    with open(context.user_data['video_path'], 'rb') as video_file:
        await update.get_bot().send_video(
            chat_id=group_id,
            message_thread_id=topic_id,
            video=video_file,
            caption=f"{context.user_data['video_title']}\n\n{context.user_data['video_description']}"
        )
    # Сохранить в БД
    db.add_video(
        context.user_data['video_topic'],
        context.user_data['video_title'],
        context.user_data['video_path'],
        context.user_data['video_description']
    )
    await update.message.reply_text("Видео добавлено и опубликовано!", reply_markup=get_main_keyboard_admin())
    context.user_data.clear()
    return ConversationHandler.END

async def handle_change_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите новую цену подписки (в рублях):",
        reply_markup=get_back_keyboard()
    )
    return CHANGE_PRICE

async def save_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "Главное меню администратора",
            reply_markup=get_main_keyboard_admin()
        )
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(
            "Введите число.",
            reply_markup=get_back_keyboard()
        )
        return CHANGE_PRICE
    
    new_price = int(text)
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE settings SET price = ?", (new_price,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Цена обновлена.",
        reply_markup=get_main_keyboard_admin()
    )
    return ConversationHandler.END

async def handle_change_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите новый период подписки (в месяцах):",
        reply_markup=get_back_keyboard()
    )
    return CHANGE_PERIOD

async def save_new_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "Главное меню администратора",
            reply_markup=get_main_keyboard_admin()
        )
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(
            "Введите число.",
            reply_markup=get_back_keyboard()
        )
        return CHANGE_PERIOD
    
    new_period = int(text)
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE settings SET period = ?", (new_period,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Период подписки обновлён.",
        reply_markup=get_main_keyboard_admin()
    )
    return ConversationHandler.END

async def handle_change_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите новое описание тренера:",
        reply_markup=get_back_keyboard()
    )
    return CHANGE_INFO

async def save_new_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "Главное меню администратора",
            reply_markup=get_main_keyboard_admin()
        )
        return ConversationHandler.END

    new_info = text
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE settings SET description = ?", (new_info,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Описание тренера обновлено.",
        reply_markup=get_main_keyboard_admin()
    )
    return ConversationHandler.END

async def handle_change_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введите новые контактные данные:",
        reply_markup=get_back_keyboard()
    )
    return CHANGE_CONTACTS

async def save_new_contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "Главное меню администратора",
            reply_markup=get_main_keyboard_admin()
        )
        return ConversationHandler.END

    new_contacts = text
    conn = sqlite3.connect(db.DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE settings SET contacts = ?", (new_contacts,))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Контактные данные обновлены.",
        reply_markup=get_main_keyboard_admin()
    )
    return ConversationHandler.END


async def handle_back_to_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Главное меню администратора:",
        reply_markup=get_main_keyboard_admin()
    )
    return ConversationHandler.END