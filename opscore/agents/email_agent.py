"""EmailAgent — Classifies threads, summarizes inbox, generates context-aware drafts."""

import asyncio
from opscore.services import gmail_service


class EmailAgent:
    """Agent responsible for email classification, summarization, and draft generation."""

    name = "EmailAgent"

    async def fetch_and_classify(self, credentials) -> dict:
        """Fetch recent emails and format them for the orchestrator pipeline.
        
        Returns dict with raw data and formatted prompt string.
        """
        raw_emails = await asyncio.to_thread(
            gmail_service.fetch_recent_emails, credentials
        )
        formatted = gmail_service.format_emails_for_prompt(raw_emails)
        return {
            "raw": raw_emails,
            "formatted": formatted,
            "agent": self.name,
        }
