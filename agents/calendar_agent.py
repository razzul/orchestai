# agents/calendar_agent.py
import google.generativeai as genai
from tools.calendar_mcp import create_calendar_event, list_calendar_events, delete_calendar_event
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def run_calendar_agent(instruction: str) -> str:
    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are a calendar manager. The user said: "{instruction}"

    Respond ONLY with a JSON object like one of these:
    {{"action": "create_event", "summary": "...", "start_time": "2025-07-28T10:00:00", "end_time": "2025-07-28T11:00:00", "description": "..."}}
    OR
    {{"action": "list_events", "date": "2025-07-28"}}
    OR
    {{"action": "delete_event", "event_id": "..."}}
    """
    response = model.generate_content(prompt)
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)

    if data["action"] == "create_event":
        result = create_calendar_event(
            data["summary"],
            data["start_time"],
            data["end_time"],
            data.get("description", "")
        )
        return f"Event created: {result}"
    elif data["action"] == "list_events":
        events = list_calendar_events(data["date"])
        return f"Events on {data['date']}: {json.dumps(events)}"
    elif data["action"] == "delete_event":
        result = delete_calendar_event(data["event_id"])
        return f"Event deleted: {result}"
    return "Calendar operation completed."