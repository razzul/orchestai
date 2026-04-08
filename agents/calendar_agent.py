# agents/calendar_agent.py
import google.generativeai as genai
from tools.calendar_mcp import create_calendar_event, list_calendar_events, delete_calendar_event
import os, json

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


async def run_calendar_agent(instruction: str, history: list = None) -> dict:
    model = genai.GenerativeModel("gemini-3-flash-preview")
    
    context = ""
    if history:
        context = "Session context:\n" + "\n".join([f"{m['role']}: {m['content']}" for m in history[-5:]])

    prompt = f"""
    You are a calendar manager. 
    
    {context}
    
    The user's current request is: "{instruction}"

    Based on the context and current request, respond ONLY with a JSON object like one of these:
    {{"action": "create_event", "summary": "...", "start_time": "2025-07-28T10:00:00", "end_time": "2025-07-28T11:00:00", "description": "..."}}
    OR
    {{"action": "list_events", "date": "2025-07-28"}}
    OR
    {{"action": "delete_event", "event_id": "..."}}
    
    If information is missing from the current request but available in context, use it.
    """
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"Calendar agent AI error: {e}")
        return {
            "response": "I couldn't process the calendar request. It might be missing details like event time.",
            "log_entry": f"CAL_AI_ERROR: {str(e)[:50]}",
            "tag_label": "Calendar error"
        }

    try:
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
                "log_entry": f"MCP gcal.create_event {data['summary']} at {time_str}",
                "tag_label": f"Thu {time_str} blocked"  # Matches user requested style
            }
        elif data["action"] == "list_events":
            events = list_calendar_events(data["date"])
            return {
                "response": f"Events on {data['date']}: {json.dumps(events)}",
                "log_entry": f"MCP gcal.list_events for {data['date']}",
                "tag_label": "Events listed"
            }
        elif data["action"] == "delete_event":
            result = delete_calendar_event(data["event_id"])
            return {
                "response": f"Event deleted: {result}",
                "log_entry": f"MCP gcal.delete_event {data['event_id'][:8]}...",
                "tag_label": "Event deleted"
            }
    except Exception as e:
        print(f"Calendar agent tool error: {e}")
        return {
            "response": f"Calendar tool error: {e}",
            "log_entry": f"CAL_TOOL_ERROR: {str(e)[:50]}",
            "tag_label": "Calendar failed"
        }

    return {"response": "Calendar operation completed.", "log_entry": "CAL_NOP", "tag_label": "Calendar done"}