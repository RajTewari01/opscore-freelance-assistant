"""AI Service API integration — google.genai for Gemini, litellm for other providers."""

import json
import re
import litellm
from google import genai

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


def get_model_string(provider: str) -> str:
    """Map the frontend provider ID to the exact routing string."""
    if not provider or provider == "gemini":
        return "gemini/gemini-2.0-flash"
        
    if "/" in provider:
        # Strip any stale -latest suffix from cached selections
        sanitized = provider.replace("-latest", "")
        # Redirect any retired 1.5/1.0 models to 2.0-flash
        if "gemini-1.5" in sanitized or "gemini-1.0" in sanitized or sanitized == "gemini/gemini-pro":
            return "gemini/gemini-2.0-flash"
        return sanitized
        
    if provider == "openai":
        return "gpt-4o-mini"
    elif provider == "anthropic":
        return "claude-3-haiku-20240320"
    elif provider == "grok":
        return "xai/grok-beta"
    else:
        return "gemini/gemini-2.0-flash"


def build_prompt(email_summaries: str, calendar_events: str, drive_files: str) -> str:
    """Build the structured prompt from all three data sources."""
    return PROMPT_TEMPLATE.format(
        email_summaries=email_summaries,
        calendar_events=calendar_events,
        drive_files=drive_files,
    )


def parse_json_fallback(raw_text: str) -> dict:
    """Safely extract JSON payload even if the LLM hallucinates markdown wrappers."""
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])
    if raw_text.lower().startswith("json"):
        raw_text = raw_text[4:].strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw_text)
        if match:
            return json.loads(match.group(0))
        raise


def analyze_context(context_prompt: str, provider: str = None, api_key: str = None) -> AnalysisResponse:
    """Send the assembled prompt to the selected Provider and parse the JSON response."""
    model_str = get_model_string(provider)
    api_key_val = api_key if api_key else settings.GEMINI_API_KEY

    if not api_key_val:
        raise ValueError("Missing API Key: Please enter your provider API Key in the Settings menu.")

    # Native google.genai for Gemini models (uses v1 API, not deprecated v1beta)
    if model_str.startswith("gemini/"):
        client = genai.Client(api_key=api_key_val)
        bare_model = model_str.replace("gemini/", "")
        response = client.models.generate_content(
            model=bare_model,
            contents=context_prompt,
        )
        raw_text = response.text
    else:
        # LiteLLM for OpenAI / Anthropic / xAI
        response = litellm.completion(
            model=model_str,
            messages=[{"role": "user", "content": context_prompt}],
            api_key=api_key_val
        )
        raw_text = response.choices[0].message.content
    parsed = parse_json_fallback(raw_text)

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


def execute_action_prompt(prompt: str, expect_json: bool = False, provider: str = None, api_key: str = None) -> str:
    """Executes a generic Multi-Model prompt for specific micro-actions (summarize, draft, graphify)."""
    model_str = get_model_string(provider)
    api_key_val = api_key if api_key else settings.GEMINI_API_KEY
    
    if model_str.startswith("gemini/"):
        client = genai.Client(api_key=api_key_val)
        bare_model = model_str.replace("gemini/", "")
        response = client.models.generate_content(
            model=bare_model,
            contents=prompt,
        )
        return response.text
    else:
        response = litellm.completion(
            model=model_str,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key_val
        )
        return response.choices[0].message.content
