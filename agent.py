import base64, json, datetime, os
from google import genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ── Gmail ─────────────────────────────────────────────────────────────────────

def get_gmail_service(token_json: dict):
    """Build Gmail service from a stored token dict."""
    creds = Credentials.from_authorized_user_info(token_json, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds), json.loads(creds.to_json())

def extract_body(payload):
    if "parts" in payload:
        for p in payload["parts"]:
            if p["mimeType"] == "text/plain" and p["body"].get("data"):
                return base64.urlsafe_b64decode(
                    p["body"]["data"]).decode("utf-8", "ignore")
            if "parts" in p:
                return extract_body(p)
    elif payload["body"].get("data"):
        return base64.urlsafe_b64decode(
            payload["body"]["data"]).decode("utf-8", "ignore")
    return ""

def fetch_emails(service, days: int = 1):
    after = int((datetime.datetime.now() -
                 datetime.timedelta(days=days)).timestamp())
    res = service.users().messages().list(
        userId="me",
        q=f"after:{after} -category:promotions -category:social",
        maxResults=40
    ).execute()
    msgs = res.get("messages", [])
    emails = []
    for m in msgs:
        d = service.users().messages().get(
            userId="me", id=m["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in d["payload"]["headers"]}
        body = extract_body(d["payload"])
        emails.append({
            "from":    headers.get("From", ""),
            "subject": headers.get("Subject", "(no subject)"),
            "snippet": d.get("snippet", ""),
            "body":    body[:1500],
        })
    return emails

# ── Gemini ────────────────────────────────────────────────────────────────────

def analyze(emails: list) -> list:
    if not emails:
        return []
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    payload = [
        {"i": i, "from": e["from"], "subject": e["subject"],
         "text": e["snippet"] + " " + e["body"]}
        for i, e in enumerate(emails)
    ]
    prompt = f"""You are an email assistant for a university student.
From the emails below, KEEP only those about: hackathons, workshops, internships,
academic matters (exams, results, deadlines, registration), or scholarships.
IGNORE newsletters, promotions, spam, OTPs, and irrelevant mail.

For each KEPT email return JSON with:
- category (one of: hackathon, workshop, internship, academic, scholarship)
- priority (high/medium/low)
- summary (1 short line)
- deadline (date/time if mentioned, else "none")

Return ONLY a JSON array. No markdown, no backticks. Emails:
{json.dumps(payload)}"""

    resp = client.models.generate_content(
        model="gemini-2.5-flash", contents=prompt)
    txt = resp.text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(txt)
    except Exception:
        return []

# ── Digest builder ────────────────────────────────────────────────────────────

def build_digest(items: list, name: str = "") -> str:
    greeting = f"Hey {name}! " if name else ""
    if not items:
        return (f"📭 *UniMail Digest*\n\n"
                f"{greeting}Nothing important in the last 24h. Enjoy your day! 🎉")

    icons = {"hackathon": "🏆", "workshop": "🛠️", "internship": "💼",
             "academic": "📚", "scholarship": "🎓"}
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: order.get(x.get("priority", "low"), 3))
    today = datetime.date.today().strftime("%d %b %Y")
    lines = [f"📬 *UniMail Digest — {today}*", ""]
    for it in items:
        ic = icons.get(it.get("category"), "•")
        flag = "🔴 " if it.get("priority") == "high" else ""
        line = f"{ic} {flag}*{it.get('category','').title()}* — {it.get('summary','')}"
        if it.get("deadline", "none") not in ("none", "", None):
            line += f"\n   ⏰ _Deadline: {it['deadline']}_"
        lines.append(line)
    lines.append(f"\n_Total: {len(items)} relevant emails_")
    return "\n".join(lines)
