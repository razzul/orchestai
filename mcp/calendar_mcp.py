# mcp/calendar_mcp.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timezone
import json

def get_calendar_service():
    with open("calendar_token.json", "r") as f:
        token_data = json.load(f)
    creds = Credentials.from_authorized_user_info(token_data)
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> dict:
    """
    Creates a Google Calendar event.
    start_time and end_time must be ISO format strings e.g. '2025-07-28T10:00:00'
    """
    service = get_calendar_service()
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "UTC"},
        "end": {"dateTime": end_time, "timeZone": "UTC"},
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return {"event_id": result["id"], "link": result.get("htmlLink"), "status": "created"}


def list_calendar_events(date: str) -> list:
    """
    Lists events for a given date. date format: 'YYYY-MM-DD'
    """
    service = get_calendar_service()
    time_min = f"{date}T00:00:00Z"
    time_max = f"{date}T23:59:59Z"
    result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = result.get("items", [])
    return [{"id": e["id"], "summary": e.get("summary"), "start": e["start"].get("dateTime")} for e in events]


def delete_calendar_event(event_id: str) -> dict:
    service = get_calendar_service()
    service.events().delete(calendarId="primary", eventId=event_id).execute()
    return {"status": "deleted", "event_id": event_id}