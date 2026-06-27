import os, json, tempfile, requests as req
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GRequest
from googleapiclient.discovery import build
from database import init_db, save_user_token

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

SCOPES       = ["https://www.googleapis.com/auth/gmail.readonly"]
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourUniMailBot")
BASE_URL     = os.getenv("BASE_URL", "http://localhost:8000")

app = FastAPI(title="UniMail")

@app.on_event("startup")
def startup():
    init_db()

# ── helpers ───────────────────────────────────────────────────────────────────

def get_client_info():
    """Return (client_id, client_secret) from env or credentials.json."""
    raw = os.getenv("GOOGLE_CLIENT_SECRET_JSON")
    if raw:
        data = json.loads(raw)
    else:
        with open("credentials.json") as f:
            data = json.load(f)
    # supports both "web" and "installed" key
    info = data.get("web") or data.get("installed")
    return info["client_id"], info["client_secret"]

REDIRECT_URI = f"{BASE_URL}/auth/callback"

# ── Home page ─────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
def home():
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UniMail — AI Email Digest for Students</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Segoe UI',sans-serif;background:#F5F2FF;
         display:flex;align-items:center;justify-content:center;min-height:100vh}}
    .card{{background:#fff;border-radius:20px;padding:48px 40px;
           max-width:480px;width:90%;text-align:center;
           box-shadow:0 4px 32px rgba(124,92,191,.10)}}
    .logo{{font-size:48px;margin-bottom:12px}}
    h1{{font-size:28px;color:#2D2040;margin-bottom:8px}}
    p{{color:#9B88CC;font-size:15px;line-height:1.6;margin-bottom:28px}}
    .steps{{text-align:left;background:#F5F2FF;border-radius:12px;
            padding:20px 24px;margin-bottom:28px}}
    .steps li{{color:#2D2040;font-size:14px;margin-bottom:10px;padding-left:8px}}
    .btn{{display:inline-block;background:#7C5CBF;color:#fff;
          padding:14px 36px;border-radius:10px;font-size:15px;
          font-weight:600;text-decoration:none;transition:background .2s}}
    .btn:hover{{background:#6A4BAA}}
    .note{{color:#B8AED8;font-size:12px;margin-top:20px}}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">📬</div>
    <h1>UniMail</h1>
    <p>AI-powered Gmail digest for university students.<br>
       Get only the emails that matter, straight to Telegram.</p>
    <div class="steps"><ol>
      <li>Click below to connect your Gmail</li>
      <li>Open Telegram and start <strong>@{BOT_USERNAME}</strong></li>
      <li>Type <code>/run</code> to get your digest instantly</li>
    </ol></div>
    <a class="btn" href="/auth/start">Connect Gmail →</a>
    <p class="note">We only read your emails. We never store email content.</p>
  </div>
</body>
</html>"""

# ── Step 1: Redirect to Google ────────────────────────────────────────────────
@app.get("/auth/start")
def auth_start(tg: str = "", name: str = ""):
    client_id, _ = get_client_info()
    state = f"{tg}|{name}"
    params = {
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         state,
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + \
               "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(auth_url)

# ── Step 2: Google sends the code here ───────────────────────────────────────
@app.get("/auth/callback")
def auth_callback(code: str = "", state: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"<h2>Error: {error}</h2>", status_code=400)

    client_id, client_secret = get_client_info()

    # Exchange code for tokens — plain HTTP POST, no PKCE required
    token_resp = req.post("https://oauth2.googleapis.com/token", data={
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    })
    token_data = token_resp.json()

    if "error" in token_data:
        return HTMLResponse(
            f"<h2>Token error: {token_data}</h2>", status_code=400)

    # Build a Credentials object and get Gmail profile
    creds = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    svc = build("gmail", "v1", credentials=creds)
    profile     = svc.users().getProfile(userId="me").execute()
    gmail_email = profile.get("emailAddress", "")

    # Parse telegram_id and name from state
    parts         = state.split("|", 1)
    telegram_id   = parts[0] if parts else ""
    telegram_name = parts[1] if len(parts) > 1 else ""

    # Store in DB
    save_user_token(
        telegram_id=telegram_id,
        telegram_name=telegram_name,
        gmail_email=gmail_email,
        token_json=json.loads(creds.to_json()),
    )

    return HTMLResponse(f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><title>Connected!</title>
  <style>
    body{{font-family:'Segoe UI',sans-serif;background:#F5F2FF;
         display:flex;align-items:center;justify-content:center;min-height:100vh}}
    .card{{background:#fff;border-radius:20px;padding:48px 40px;
           max-width:420px;text-align:center;
           box-shadow:0 4px 32px rgba(124,92,191,.10)}}
    h1{{color:#2D2040;margin:16px 0 8px;font-size:24px}}
    p{{color:#9B88CC;font-size:15px;line-height:1.6}}
    .email{{background:#EDE8FB;color:#7C5CBF;padding:6px 14px;
            border-radius:8px;font-weight:600;display:inline-block;margin:12px 0 20px}}
    code{{background:#F5F2FF;padding:2px 8px;border-radius:6px;
          color:#7C5CBF;font-weight:700}}
  </style>
</head>
<body>
  <div class="card">
    <div style="font-size:52px">🎉</div>
    <h1>You're connected!</h1>
    <div class="email">{gmail_email}</div>
    <p>Head back to Telegram and type <code>/run</code><br>
       to get your first email digest!</p>
  </div>
</body>
</html>""")