"""Google Calendar API integration — fetches today's calendar events."""

from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build


def get_calendar_service(credentials):
    """Build an authorized Google Calendar API client."""
    return build("calendar", "v3", credentials=credentials)


def fetch_todays_events(credentials) -> list[dict]:
    """Fetch all events scheduled for today from the primary calendar."""
    service = get_calendar_service(credentials)

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    raw_events = events_result.get("items", [])
    calendar_events = []

    for event in raw_events:
        start = event.get("start", {})
        end = event.get("end", {})
        calendar_events.append({
            "summary": event.get("summary", "(No Title)"),
            "start": start.get("dateTime", start.get("date", "Unknown")),
            "end": end.get("dateTime", end.get("date", "Unknown")),
            "location": event.get("location", ""),
            "description": event.get("description", ""),
        })

    return calendar_events


def format_events_for_prompt(calendar_events: list[dict]) -> str:
    """Format calendar events into a string for the Gemini prompt."""
    if not calendar_events:
        return "No events scheduled for today."

    lines = []
    for index, event in enumerate(calendar_events, 1):
        location_text = f" | Location: {event['location']}" if event["location"] else ""
        lines.append(
            f"{index}. {event['summary']}\n"
            f"   Time: {event['start']} → {event['end']}{location_text}"
        )
    return "\n\n".join(lines)
