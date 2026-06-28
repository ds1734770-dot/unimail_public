"""
main.py — runs FastAPI web app and Telegram bot together.
Also pings itself every 10 minutes to prevent Render free tier sleep.
"""
import asyncio, os, threading, uvicorn, requests, time
from dotenv import load_dotenv

load_dotenv()

def keep_alive():
    """Ping the app every 10 minutes to prevent Render sleep."""
    url = os.getenv("BASE_URL", "http://localhost:8000")
    time.sleep(60)  # wait 1 min for app to fully start first
    while True:
        try:
            requests.get(url, timeout=10)
            print(f"✅ Keep-alive ping sent to {url}")
        except Exception as e:
            print(f"⚠️ Keep-alive ping failed: {e}")
        time.sleep(600)  # ping every 10 minutes

def run_bot():
    """Run Telegram bot in a separate thread."""
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

def run_webapp():
    """Run FastAPI on the port Render assigns."""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("webapp:app", host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    print("🚀 UniMail starting...")

    # Start keep-alive in background
    ka_thread = threading.Thread(target=keep_alive, daemon=True)
    ka_thread.start()

    # Start bot in background
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Run web app in main thread
    run_webapp()