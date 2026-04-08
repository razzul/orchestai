# agents/comms_agent.py
import google.generativeai as genai
from mcp.gmail_mcp import send_email, list_emails, draft_email
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def run_comms_agent(instruction: str) -> str:
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are an email manager. The user said: "{instruction}"

    Respond ONLY with a JSON object like one of these:
    {{"action": "send_email", "to": "someone@email.com", "subject": "...", "body": "..."}}
    OR
    {{"action": "list_emails", "query": "from:boss@company.com"}}
    OR
    {{"action": "draft_email", "to": "someone@email.com", "subject": "...", "body": "..."}}
    """
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)

    if data["action"] == "send_email":
        result = send_email(data["to"], data["subject"], data["body"])
        return f"Email sent: {result}"
    elif data["action"] == "list_emails":
        emails = list_emails(data.get("query", ""))
        return f"Emails found: {json.dumps(emails)}"
    elif data["action"] == "draft_email":
        result = draft_email(data["to"], data["subject"], data["body"])
        return f"Draft created: {result}"
    return "Email operation completed."