import sqlite3

DB_PATH = 'users.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Таблица пользователей
    c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, 
                username TEXT,
                is_paid BOOLEAN,
                payment_date TEXT,
                data_end TEXT)''')
    # Таблица для хранения env
    c.execute('''
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
                topic_name TEXT)''')
    
    #Таблица для хранения видео
    c.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_topic TEXT, 
                title TEXT,
                file_path TEXT,
                description TEXT)''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS topics (
            thread_id INTEGER PRIMARY KEY,
            topic_name TEXT UNIQUE
        )
    ''')

    conn.commit()
    conn.close()

def init_settings_with_defaults():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM settings')
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO settings (price, period, admin_usernames, description_coach, support_concat, bank_token, bot_token, link_chanal, chat_id, topic_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                        2000,
                        3,
                        '424576017, 00000000',
                        'Максим Александрович, четырех кратный победитель кубка галактики, трехкратный призер дворовых игр без правил и просто капитальный красавчик',
                        'Связь по вопросам: @am_vasilev',
                        'None',
                        '7529079621:AAEpT2cVdiDmQHFmTT_11QVY4IOQrlVlRT8',
                        'https://t.me/+_8ozeq-tQnlhODJi',
                        -1002624676766,
                        'Обоюдный захват, Партер, Захват голова с рукой, Посадки с высокого партера, Работа на руках, Работа на проходах, Физическая подготовка, Скоростно-силовая подготовка'
                    )
                )
    conn.commit()
    conn.close()

def save_topic(thread_id: int, topic_name: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO topics (thread_id, topic_name)
        VALUES (?, ?)
        ON CONFLICT(thread_id) DO UPDATE SET topic_name = excluded.topic_name
    ''', (thread_id, topic_name))
    conn.commit()
    conn.close()


def get_setting(key: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f'SELECT {key} FROM settings LIMIT 1')
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def load_env():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT price, period, admin_usernames, description_coach, support_concat, bank_token, bot_token, link_chanal FROM settings LIMIT 1")
    row = c.fetchone()  # Получаем одну строку
    conn.close()  # Закрываем соединение
    
    if row:
        price, period, admin_usernames, description_coach, support_concat, bank_token, bot_token, link_chanal = row
        return price, period, admin_usernames, description_coach, support_concat, bank_token, bot_token, link_chanal
    else:
        return None

def is_user_paid(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT is_paid FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row[0]) if row else False

def add_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, is_paid) VALUES (?, ?, ?)",
              (user_id, username, False))
    conn.commit()
    conn.close()

def add_video(title: str, file_path: str, description: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO videos (title, file_path, description) VALUES (?, ?, ?)', (title, file_path, description))
    conn.commit()
    conn.close()


def get_all_videos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, title, file_path, description FROM videos')
    rows = c.fetchall()
    conn.close()
    return rows

def get_topics_from_settings():
    topics_str = get_setting('topic_name')
    if not topics_str:
        return []
    return [t.strip() for t in topics_str.split(',') if t.strip()]

#init_db()
#init_settings_with_defaults()
