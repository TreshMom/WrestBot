import sqlite3

DB_PATH = "users.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Таблица пользователей
    c.execute("""
                CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                username TEXT,
                is_paid BOOLEAN,
                payment_date TEXT,
                data_end TEXT)""")
    # Таблица для хранения env
    c.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                price INTEGER,
                period INTEGER,
                admin_usernames TEXT,
                description_coach TEXT,
                support_concat TEXT,
                bank_token TEXT,
                bot_token TEXT,
                link_chanal TEXT,
                chat_id INTEGER,
                text_payment TEXT)""")
    
    conn.commit()
    conn.close()


def init_settings_with_defaults():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM settings")
    if c.fetchone()[0] == 0:
        c.execute(
            """
            INSERT INTO settings (admin_usernames, bank_token, bot_token, link_chanal, chat_id, price, period, text_payment, description_coach, support_concat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "424576017, 956627095",
                "None",
                "None",
                "None",
                None,
                1000,
                1,
                "Тут должен быть текст оплаты",
                "Тут должна быть информация о тренере",
                "@temmp_support",
            ),
        )
    conn.commit()
    conn.close()


def save_topic(thread_id: int, topic_name: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO topics (thread_id, topic_name)
        VALUES (?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET topic_name = excluded.topic_name
    """,
        (thread_id, topic_name),
    )
    conn.commit()
    conn.close()


def get_setting(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT {key} FROM settings LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def is_user_paid(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT is_paid FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False


def get_user_subscription_end(user_id: int) -> str:
    """Получает дату окончания подписки пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT data_end FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


#init_db()
#init_settings_with_defaults()
