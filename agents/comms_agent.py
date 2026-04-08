# agents/comms_agent.py
import google.generativeai as genai
from tools.gmail_mcp import send_email, list_emails, draft_email
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def run_comms_agent(instruction: str) -> str:
    model = genai.GenerativeModel("gemini-3-flash-preview")
    prompt = f"""
    You are an email manager. The user said: "{instruction}"

    Respond ONLY with a JSON object like one of these:
    {{"action": "send_email", "to": "someone@email.com", "subject": "...", "body": "...", "recipient_name": "Sarah"}}
    OR
    {{"action": "list_emails", "query": "from:boss@company.com"}}
    OR
    {{"action": "draft_email", "to": "someone@email.com", "subject": "...", "body": "..."}}
    """
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"Comms agent error: {e}")
        return {"response": "I'm having trouble with your email request right now.", "log_entry": "COMMS_ERROR", "tag_label": "Email error"}

    if data["action"] == "send_email":
        result = send_email(data["to"], data["subject"], data["body"])
        recipient = data.get("recipient_name") or data["to"].split("@")[0]
        return {
            "response": f"Email sent: {result}",
            "log_entry": f"MCP gmail.send to {data['to']}",
            "tag_label": f"Email sent to {recipient}"
        }
    elif data["action"] == "list_emails":
        emails = list_emails(data.get("query", ""))
        return {
            "response": f"Emails found: {json.dumps(emails)}",
            "log_entry": f"MCP gmail.list_emails query: {data.get('query', 'all')}",
            "tag_label": "Emails found"
        }
    elif data["action"] == "draft_email":
        result = draft_email(data["to"], data["subject"], data["body"])
        return {
            "response": f"Draft created: {result}",
            "log_entry": f"MCP gmail.draft to {data['to']}",
            "tag_label": "Draft created"
        }
    return {"response": "Email operation completed.", "log_entry": "EMAIL_NOP", "tag_label": "Email done"}