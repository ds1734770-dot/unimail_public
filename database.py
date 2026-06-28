"""
database.py — PostgreSQL version for Render deployment.
Falls back to SQLite for local development automatically.
"""
import os, json

DATABASE_URL = os.getenv("DATABASE_URL", "")

# ── Detect which DB to use ────────────────────────────────────────────────────
USE_POSTGRES = DATABASE_URL.startswith("postgres")

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Render gives postgres:// but psycopg2 needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    import sqlite3

# ── Connection ────────────────────────────────────────────────────────────────

def get_conn():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        conn = sqlite3.connect("unimail.db")
        conn.row_factory = sqlite3.Row
        return conn

# ── Init ──────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id     TEXT PRIMARY KEY,
                telegram_name   TEXT,
                gmail_email     TEXT,
                gmail_token     TEXT,
                registered_at   TIMESTAMP DEFAULT NOW(),
                last_run        TIMESTAMP
            )
        """)
    else:
        cur.execute("""
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
    cur.close()
    conn.close()
    db_type = "PostgreSQL" if USE_POSTGRES else "SQLite"
    print(f"Database initialised ({db_type}).")

# ── Save/update user token ────────────────────────────────────────────────────

def save_user_token(telegram_id: str, telegram_name: str,
                    gmail_email: str, token_json: dict):
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            INSERT INTO users (telegram_id, telegram_name, gmail_email, gmail_token)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
                gmail_email   = EXCLUDED.gmail_email,
                gmail_token   = EXCLUDED.gmail_token,
                telegram_name = EXCLUDED.telegram_name
        """, (telegram_id, telegram_name, gmail_email,
              json.dumps(token_json)))
    else:
        conn.execute("""
            INSERT INTO users (telegram_id, telegram_name, gmail_email, gmail_token)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                gmail_email   = excluded.gmail_email,
                gmail_token   = excluded.gmail_token,
                telegram_name = excluded.telegram_name
        """, (telegram_id, telegram_name, gmail_email,
              json.dumps(token_json)))
    conn.commit()
    cur.close() if USE_POSTGRES else None
    conn.close()

# ── Get single user ───────────────────────────────────────────────────────────

def get_user(telegram_id: str):
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    else:
        row = conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

# ── Update last run time ──────────────────────────────────────────────────────

def update_last_run(telegram_id: str):
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            UPDATE users SET last_run = NOW()
            WHERE telegram_id = %s
        """, (telegram_id,))
    else:
        conn.execute("""
            UPDATE users SET last_run = datetime('now')
            WHERE telegram_id = ?
        """, (telegram_id,))
    conn.commit()
    cur.close() if USE_POSTGRES else None
    conn.close()

# ── Get all users ─────────────────────────────────────────────────────────────

def get_all_users():
    conn = get_conn()
    cur  = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "SELECT * FROM users WHERE gmail_token IS NOT NULL")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) for r in rows]
    else:
        rows = conn.execute(
            "SELECT * FROM users WHERE gmail_token IS NOT NULL"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]