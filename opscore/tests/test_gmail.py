"""Tests for Gmail service — mocked API, asserts email summaries are extracted correctly."""

from unittest.mock import MagicMock, patch

from opscore.services.gmail_service import fetch_recent_emails, format_emails_for_prompt


class TestFetchRecentEmails:
    """Test suite for Gmail email fetching and formatting."""

    @patch("opscore.services.gmail_service.build")
    def test_fetch_recent_emails_returns_structured_summaries(self, mock_build):
        """Verify that fetched emails are parsed into structured dictionaries."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg_001"}]
        }
        mock_service.users().messages().get().execute.return_value = {
            "payload": {
                "headers": [
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "Subject", "value": "Project Update"},
                    {"name": "Date", "value": "Mon, 19 Apr 2026 10:00:00 +0000"},
                ]
            },
            "snippet": "Hi, here is the latest update on the project...",
        }

        credentials = MagicMock()
        result = fetch_recent_emails(credentials)

        assert len(result) == 1
        assert result[0]["from"] == "alice@example.com"
        assert result[0]["subject"] == "Project Update"
        assert "latest update" in result[0]["snippet"]

    def test_format_emails_for_prompt_with_data(self):
        """Verify email summaries are formatted into a readable prompt string."""
        emails = [
            {
                "from": "bob@client.com",
                "subject": "Invoice Due",
                "date": "Tue, 20 Apr 2026 08:00:00 +0000",
                "snippet": "Payment reminder for April services.",
            }
        ]
        result = format_emails_for_prompt(emails)

        assert "bob@client.com" in result
        assert "Invoice Due" in result
        assert "Payment reminder" in result

    def test_format_emails_for_prompt_empty_list(self):
        """Verify empty email list returns a descriptive fallback message."""
        result = format_emails_for_prompt([])
        assert result == "No recent emails found."
