"""
main.py — runs the FastAPI web app and Telegram bot together in one process.
Railway runs this single file via: python main.py
"""
import asyncio, os, threading, uvicorn
from dotenv import load_dotenv

load_dotenv()

def run_webapp():
    """Run FastAPI on port 8000 (Railway sets PORT env var)."""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("webapp:app", host="0.0.0.0", port=port, log_level="info")

def run_bot():
    """Run Telegram bot in a separate thread."""
    import bot as telegram_bot
    from telegram.ext import ApplicationBuilder, CommandHandler
    from bot import cmd_start, cmd_connect, cmd_run, cmd_status, cmd_help
    from database import init_db

    init_db()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("connect", cmd_connect))
    app.add_handler(CommandHandler("run",     cmd_run))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("help",    cmd_help))
    print("🤖 Telegram bot started")
    app.run_polling()

if __name__ == "__main__":
    print("🚀 UniMail starting...")
    # Run bot in background thread, web app in main thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    run_webapp()
