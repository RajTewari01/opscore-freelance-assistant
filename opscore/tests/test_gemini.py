"""Tests for Gemini service — mocked response, asserts JSON is parsed into correct Pydantic model."""

from unittest.mock import MagicMock, patch
import json

from opscore.services.gemini_service import analyze_context, build_prompt
from opscore.models.schemas import AnalysisResponse


MOCK_GEMINI_RESPONSE = json.dumps({
    "priority_queue": [
        {"rank": 1, "task": "Reply to client invoice", "reason": "Payment overdue by 3 days", "urgency": "high"},
        {"rank": 2, "task": "Review PR #42", "reason": "Blocking team progress", "urgency": "medium"},
        {"rank": 3, "task": "Update project docs", "reason": "Stale documentation", "urgency": "low"},
    ],
    "drafted_reply": {
        "to": "alice@client.com",
        "subject": "Re: Invoice #1024",
        "body": "Hi Alice,\n\nThank you for the reminder. I've processed the payment today.\n\nBest,\nDev",
    },
    "deadline_alert": {
        "exists": True,
        "event": "Project milestone delivery",
        "due": "2026-04-19T23:59:00Z",
        "action_needed": "Submit final deliverable to client portal",
    },
})


class TestGeminiService:
    """Test suite for Gemini prompt building and response parsing."""

    def test_build_prompt_contains_all_sections(self):
        """Verify the assembled prompt includes all three data source sections."""
        prompt = build_prompt(
            email_summaries="Email from alice@test.com",
            calendar_events="Sprint planning at 9am",
            drive_files="proposal.pdf modified today",
        )

        assert "Email from alice@test.com" in prompt
        assert "Sprint planning at 9am" in prompt
        assert "proposal.pdf modified today" in prompt
        assert "operations assistant" in prompt

    @patch("opscore.services.gemini_service.genai")
    def test_analyze_context_parses_valid_json_response(self, mock_genai):
        """Verify that a valid Gemini JSON response is parsed into AnalysisResponse."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = MOCK_GEMINI_RESPONSE
        mock_model.generate_content.return_value = mock_response

        result = analyze_context("test prompt")

        assert isinstance(result, AnalysisResponse)
        assert len(result.priority_queue) == 3
        assert result.priority_queue[0].urgency == "high"
        assert result.drafted_reply.to == "alice@client.com"
        assert result.deadline_alert.exists is True

    @patch("opscore.services.gemini_service.genai")
    def test_analyze_context_strips_markdown_fences(self, mock_genai):
        """Verify that markdown code fences are stripped before JSON parsing."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        wrapped_response = f"```json\n{MOCK_GEMINI_RESPONSE}\n```"
        mock_response = MagicMock()
        mock_response.text = wrapped_response
        mock_model.generate_content.return_value = mock_response

        result = analyze_context("test prompt")

        assert isinstance(result, AnalysisResponse)
        assert len(result.priority_queue) == 3
