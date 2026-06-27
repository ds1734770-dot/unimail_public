import sqlite3, json, os

DB_PATH = os.getenv("DB_PATH", "unimail.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id     TEXT PRIMARY KEY,
            telegram_name   TEXT,
            gmail_email     TEXT,
            gmail_token     TEXT,
            registered_at   TEXT DEFAULT (datetime('now')),
            last_run        TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialised.")

def save_user_token(telegram_id: str, telegram_name: str, gmail_email: str, token_json: dict):
    conn = get_conn()
    conn.execute("""
        INSERT INTO users (telegram_id, telegram_name, gmail_email, gmail_token)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            gmail_email  = excluded.gmail_email,
            gmail_token  = excluded.gmail_token,
            telegram_name = excluded.telegram_name
    """, (telegram_id, telegram_name, gmail_email, json.dumps(token_json)))
    conn.commit()
    conn.close()

def get_user(telegram_id: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def update_last_run(telegram_id: str):
    conn = get_conn()
    conn.execute(
        "UPDATE users SET last_run = datetime('now') WHERE telegram_id = ?",
        (telegram_id,)
    )
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users WHERE gmail_token IS NOT NULL").fetchall()
    conn.close()
    return [dict(r) for r in rows]
