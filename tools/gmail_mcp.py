# mcp/gmail_mcp.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import base64
import json
from email.mime.text import MIMEText
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(BASE_DIR, "gmail_token.json")

def get_gmail_service():
    # Attempt to load token from environment variable first (Cloud Run)
    token_str = os.environ.get("GMAIL_TOKEN_JSON")
    if token_str:
        token_data = json.loads(token_str)
    else:
        # Fallback to local file
        with open(TOKEN_PATH, "r") as f:
            token_data = json.load(f)

    creds = Credentials.from_authorized_user_info(token_data)
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str) -> dict:
    """Sends an email via Gmail."""
    service = get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"message_id": result["id"], "status": "sent"}


def list_emails(query: str = "", max_results: int = 5) -> list:
    """Lists emails matching a query."""
    service = get_gmail_service()
    result = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = result.get("messages", [])
    emails = []
    for m in messages:
        msg = service.users().messages().get(userId="me", id=m["id"], format="metadata").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        emails.append({
            "id": m["id"],
            "subject": headers.get("Subject", ""),
            "from": headers.get("From", ""),
            "date": headers.get("Date", "")
        })
    return emails


def draft_email(to: str, subject: str, body: str) -> dict:
    """Creates a Gmail draft."""
    service = get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    draft = service.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return {"draft_id": draft["id"], "status": "drafted"}