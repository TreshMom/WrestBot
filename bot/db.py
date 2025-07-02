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
            INSERT INTO settings (price, period, admin_usernames, description_coach, support_concat, bank_token, bot_token, link_chanal, chat_id, text_payment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                2000,
                3,
                "424576017, 00000000",
                "Максим Александрович, четырех кратный победитель кубка галактики, трехкратный призер дворовых игр без правил и просто капитальный красавчик",
                "@am_vasilev",
                "None",
                "None",
                "None",
                None,
                "🥋 Курс вольной борьбы\n\n 🔥 Доступ к эксклюзивным видео, техникам и тренировкам\n",
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


#init_db()
#init_settings_with_defaults()
