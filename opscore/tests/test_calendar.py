"""Tests for Calendar service — mocked API, asserts today's events are returned."""

from unittest.mock import MagicMock, patch

from opscore.services.calendar_service import fetch_todays_events, format_events_for_prompt


class TestFetchTodaysEvents:
    """Test suite for Calendar event fetching and formatting."""

    @patch("opscore.services.calendar_service.build")
    def test_fetch_todays_events_returns_structured_events(self, mock_build):
        """Verify that calendar events are parsed into structured dictionaries."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.events().list().execute.return_value = {
            "items": [
                {
                    "summary": "Sprint Planning",
                    "start": {"dateTime": "2026-04-19T09:00:00Z"},
                    "end": {"dateTime": "2026-04-19T10:00:00Z"},
                    "location": "Zoom",
                    "description": "Weekly sprint planning call",
                }
            ]
        }

        credentials = MagicMock()
        result = fetch_todays_events(credentials)

        assert len(result) == 1
        assert result[0]["summary"] == "Sprint Planning"
        assert result[0]["location"] == "Zoom"

    def test_format_events_for_prompt_with_data(self):
        """Verify calendar events are formatted into a readable prompt string."""
        events = [
            {
                "summary": "Client Call",
                "start": "2026-04-19T14:00:00Z",
                "end": "2026-04-19T15:00:00Z",
                "location": "Google Meet",
                "description": "",
            }
        ]
        result = format_events_for_prompt(events)

        assert "Client Call" in result
        assert "Google Meet" in result

    def test_format_events_for_prompt_empty_list(self):
        """Verify empty event list returns a descriptive fallback message."""
        result = format_events_for_prompt([])
        assert result == "No events scheduled for today."
