import os, json, datetime, asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from database import init_db, get_user, update_last_run, get_all_users, save_user_token
from agent import get_gmail_service, fetch_emails, analyze, build_digest

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ── /start ────────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id   = str(user.id)
    tg_name = user.first_name or "there"
    existing = get_user(tg_id)

    if existing and existing.get("gmail_token"):
        await update.message.reply_text(
            f"👋 Welcome back, *{tg_name}!*\n\n"
            f"📧 Connected Gmail: `{existing['gmail_email']}`\n\n"
            "Commands:\n"
            "/run — fetch your emails now\n"
            "/status — last run time\n"
            "/connect — reconnect a different Gmail\n"
            "/help — all commands",
            parse_mode="Markdown"
        )
    else:
        connect_url = f"{BASE_URL}/auth/start?tg={tg_id}&name={tg_name}"
        await update.message.reply_text(
            f"👋 Hey *{tg_name}!* Welcome to *UniMail Bot*\n\n"
            "I filter your university emails using AI and send you only what matters.\n\n"
            "📌 *Step 1:* Connect your Gmail:\n"
            f"{connect_url}\n\n"
            "📌 *Step 2:* Come back here and type /run\n\n"
            "_Takes 30 seconds to set up!_",
            parse_mode="Markdown"
        )

# ── /connect ──────────────────────────────────────────────────────────────────
async def cmd_connect(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id   = str(user.id)
    tg_name = user.first_name or ""
    connect_url = f"{BASE_URL}/auth/start?tg={tg_id}&name={tg_name}"
    await update.message.reply_text(
        "🔗 *Connect your Gmail*\n\n"
        f"Click this link to authorise UniMail:\n{connect_url}\n\n"
        "_After connecting, come back and type /run_",
        parse_mode="Markdown"
    )

# ── /run ──────────────────────────────────────────────────────────────────────
async def cmd_run(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user   = update.effective_user
    tg_id  = str(user.id)
    tg_name = user.first_name or ""
    record = get_user(tg_id)

    if not record or not record.get("gmail_token"):
        connect_url = f"{BASE_URL}/auth/start?tg={tg_id}&name={tg_name}"
        await update.message.reply_text(
            "⚠️ You haven't connected your Gmail yet!\n\n"
            f"👉 Connect here: {connect_url}",
        )
        return

    await update.message.reply_text("⏳ Fetching your emails...")
    try:
        token_data = json.loads(record["gmail_token"])
        svc, refreshed_token = get_gmail_service(token_data)

        # Save refreshed token if it changed
        if refreshed_token != token_data:
            save_user_token(tg_id, tg_name, record["gmail_email"], refreshed_token)

        emails = fetch_emails(svc)
        await update.message.reply_text(
            f"📥 Found *{len(emails)}* emails. Analysing with AI...",
            parse_mode="Markdown"
        )
        items  = analyze(emails)
        digest = build_digest(items, name=tg_name)
        update_last_run(tg_id)
        await update.message.reply_text(digest, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ── /status ───────────────────────────────────────────────────────────────────
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tg_id  = str(update.effective_user.id)
    record = get_user(tg_id)
    if not record:
        await update.message.reply_text(
            "You haven't signed up yet. Use /start to begin.")
        return
    last = record.get("last_run") or "Never"
    email = record.get("gmail_email") or "Not connected"
    await update.message.reply_text(
        f"📊 *Your UniMail Status*\n\n"
        f"📧 Gmail: `{email}`\n"
        f"🕐 Last run: {last}",
        parse_mode="Markdown"
    )

# ── /help ─────────────────────────────────────────────────────────────────────
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *UniMail Bot — Commands*\n\n"
        "/start — welcome and setup guide\n"
        "/connect — link your Gmail account\n"
        "/run — fetch & analyse your emails now\n"
        "/status — see your account info\n"
        "/help — show this message\n\n"
        "_Built with Gemini AI + Gmail API_",
        parse_mode="Markdown"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    print("🤖 UniMail Multi-User Bot starting...")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("connect", cmd_connect))
    app.add_handler(CommandHandler("run",     cmd_run))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("help",    cmd_help))
    print("✅ Bot is live!")
    app.run_polling()
