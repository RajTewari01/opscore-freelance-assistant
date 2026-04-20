"""CalendarAgent — Extracts deadlines, detects conflicts, suggests focus blocks."""

import asyncio
from opscore.services import calendar_service


class CalendarAgent:
    """Agent responsible for schedule analysis and conflict detection."""

    name = "CalendarAgent"

    async def fetch_and_analyze(self, credentials) -> dict:
        """Fetch today's calendar events and format them for the orchestrator pipeline.
        
        Returns dict with raw data and formatted prompt string.
        """
        raw_events = await asyncio.to_thread(
            calendar_service.fetch_todays_events, credentials
        )
        formatted = calendar_service.format_events_for_prompt(raw_events)
        return {
            "raw": raw_events,
            "formatted": formatted,
            "agent": self.name,
        }
