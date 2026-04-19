"""Gemini API integration — builds the structured prompt and parses the JSON response."""

import json

import google.generativeai as genai

from opscore.config import settings
from opscore.models.schemas import (
    AnalysisResponse,
    DeadlineAlert,
    DraftedReply,
    PriorityItem,
)

PROMPT_TEMPLATE = """You are an operations assistant for a solo freelance developer.

## Current Context
### Emails (last 10, newest first):
{email_summaries}

### Today's Calendar Events:
{calendar_events}

### Recent Drive Files (last 5):
{drive_files}

## Your Task
Respond ONLY in the following JSON format. No markdown, no explanation outside the JSON.

{{
  "priority_queue": [
    {{"rank": 1, "task": "...", "reason": "...", "urgency": "high|medium|low"}},
    {{"rank": 2, "task": "...", "reason": "...", "urgency": "high|medium|low"}},
    {{"rank": 3, "task": "...", "reason": "...", "urgency": "high|medium|low"}}
  ],
  "drafted_reply": {{
    "to": "...",
    "subject": "Re: ...",
    "body": "..."
  }},
  "deadline_alert": {{
    "exists": true,
    "event": "...",
    "due": "...",
    "action_needed": "..."
  }}
}}"""


def configure_gemini():
    """Configure the Gemini API client with the API key from settings."""
    genai.configure(api_key=settings.GEMINI_API_KEY)


def build_prompt(email_summaries: str, calendar_events: str, drive_files: str) -> str:
    """Build the structured Gemini prompt from all three data sources."""
    return PROMPT_TEMPLATE.format(
        email_summaries=email_summaries,
        calendar_events=calendar_events,
        drive_files=drive_files,
    )


def analyze_context(context_prompt: str) -> AnalysisResponse:
    """Send the assembled prompt to Gemini and parse the JSON response."""
    configure_gemini()
    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(context_prompt)
    raw_text = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    parsed = json.loads(raw_text)

    priority_queue = [
        PriorityItem(**item) for item in parsed.get("priority_queue", [])
    ]

    drafted_reply = DraftedReply(**parsed.get("drafted_reply", {
        "to": "N/A",
        "subject": "N/A",
        "body": "No reply drafted.",
    }))

    deadline_alert = DeadlineAlert(**parsed.get("deadline_alert", {
        "exists": False,
        "event": "",
        "due": "",
        "action_needed": "",
    }))

    return AnalysisResponse(
        priority_queue=priority_queue,
        drafted_reply=drafted_reply,
        deadline_alert=deadline_alert,
    )
