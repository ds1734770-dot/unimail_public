"""
main.py — Fixed version for Render deployment.
Runs FastAPI web app and Telegram bot in the same async event loop.
"""
import os, asyncio, uvicorn, requests, threading, time
from dotenv import load_dotenv

load_dotenv()

def keep_alive():
    """Ping every 10 min to prevent Render free tier sleep."""
    url = os.getenv("BASE_URL", "http://localhost:8000")
    time.sleep(90)
    while True:
        try:
            requests.get(url, timeout=10)
            print(f"✅ Keep-alive ping sent to {url}")
        except Exception as e:
            print(f"⚠️ Keep-alive failed: {e}")
        time.sleep(600)

async def run_bot_async():
    """Run Telegram bot properly in async context."""
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
    async with app:
        await app.start()
        await app.updater.start_polling()
        # Keep bot running forever
        while True:
            await asyncio.sleep(3600)

async def run_webapp_async():
    """Run FastAPI using uvicorn programmatically."""
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(
        "webapp:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Run both bot and web app concurrently in same event loop."""
    print("🚀 UniMail starting...")

    # Start keep-alive in background thread
    ka_thread = threading.Thread(target=keep_alive, daemon=True)
    ka_thread.start()

    # Run bot and web app together
    await asyncio.gather(
        run_bot_async(),
        run_webapp_async(),
    )

if __name__ == "__main__":
    asyncio.run(main())