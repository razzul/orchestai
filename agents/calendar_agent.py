# agents/calendar_agent.py
import google.generativeai as genai
from tools.calendar_mcp import create_calendar_event, list_calendar_events, delete_calendar_event
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def run_calendar_agent(instruction: str) -> str:
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
    You are a calendar manager. The user said: "{instruction}"

    Respond ONLY with a JSON object like one of these:
    {{"action": "create_event", "summary": "...", "start_time": "2025-07-28T10:00:00", "end_time": "2025-07-28T11:00:00", "description": "..."}}
    OR
    {{"action": "list_events", "date": "2025-07-28"}}
    OR
    {{"action": "delete_event", "event_id": "..."}}
    """
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"Calendar agent error: {e}")
        return {"response": "I'm having trouble with your calendar request right now.", "log_entry": "CAL_ERROR"}

    if data["action"] == "create_event":
        result = create_calendar_event(
            data["summary"],
            data["start_time"],
            data["end_time"],
            data.get("description", "")
        )
        # Extract time for log
        start_time = data.get("start_time") or ""
        time_str = start_time.split("T")[1][:5] if "T" in start_time else ("All day" if start_time else "Unknown")
        return {
            "response": f"Event created: {result}",
            "log_entry": f"MCP gcal.create_event {data['summary']} at {time_str}"
        }
    elif data["action"] == "list_events":
        events = list_calendar_events(data["date"])
        return {
            "response": f"Events on {data['date']}: {json.dumps(events)}",
            "log_entry": f"MCP gcal.list_events for {data['date']}"
        }
    elif data["action"] == "delete_event":
        result = delete_calendar_event(data["event_id"])
        return {
            "response": f"Event deleted: {result}",
            "log_entry": f"MCP gcal.delete_event {data['event_id'][:8]}..."
        }
    return {"response": "Calendar operation completed.", "log_entry": "CAL_NOP"}