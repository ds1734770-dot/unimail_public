# 📬 UniMail — AI Email Digest Bot for Students

An open-source Telegram bot that filters your university Gmail using Gemini AI and delivers only what matters — hackathons, deadlines, internships, and scholarships.

## Features
- 🤖 AI-powered email filtering (Gemini 2.5 Flash)
- 📧 Each user connects their own Gmail via OAuth
- ⚡ `/run` command triggers instant digest
- 🔴 Priority flags for urgent deadlines
- ☁️ Deployed on Railway (always online)

## How it works
1. User opens the bot on Telegram
2. Bot sends a link → user logs in with Google
3. User types `/run` → bot fetches + filters their Gmail
4. Gemini AI classifies emails and extracts deadlines
5. Clean digest sent back to Telegram

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Bot | python-telegram-bot |
| Web/OAuth | FastAPI + Google OAuth2 |
| AI | Google Gemini 2.5 Flash |
| Email | Gmail API |
| Database | SQLite |
| Hosting | Railway |

## Self-host in 10 minutes

### 1. Clone and set up
```bash
git clone https://github.com/YOUR_USERNAME/unimail-public
cd unimail-public
pip install -r requirements.txt
cp .env.example .env
```

### 2. Create a Telegram bot
- Message [@BotFather](https://t.me/BotFather)
- `/newbot` → copy the token → paste into `.env`

### 3. Set up Google OAuth
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a project → enable Gmail API
- OAuth consent screen → External
- Create credentials → **Web application** (not Desktop!)
- Add redirect URI: `https://YOUR_RAILWAY_URL/auth/callback`
- Download JSON → paste entire content as `GOOGLE_CLIENT_SECRET_JSON` in `.env`

### 4. Get Gemini API key
- Go to [AI Studio](https://aistudio.google.com/apikey)
- Create key → paste into `.env`

### 5. Deploy to Railway
- Push to GitHub
- Connect repo on [Railway](https://railway.app)
- Add all `.env` variables in Railway's Variables tab
- Set `BASE_URL` to your Railway URL

## Environment Variables
| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `GEMINI_API_KEY` | From AI Studio |
| `BASE_URL` | Your Railway deployment URL |
| `BOT_USERNAME` | Your bot's username (no @) |
| `GOOGLE_CLIENT_SECRET_JSON` | Full contents of credentials.json |

## Contributing
PRs welcome! Ideas for improvement:
- Weekly digest scheduling
- Category filtering preferences
- Multiple Gmail accounts per user

---
Built by [Santhosh](https://github.com/ds1734770-dot) • B.Tech AIML Student
