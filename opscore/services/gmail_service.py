"""Gmail API integration — fetches and summarizes the user's last 10 emails."""

from googleapiclient.discovery import build


def get_gmail_service(credentials):
    """Build an authorized Gmail API client."""
    return build("gmail", "v1", credentials=credentials)


def fetch_recent_emails(credentials) -> list[dict]:
    """Fetch the last 10 emails and return structured summaries."""
    service = get_gmail_service(credentials)
    results = service.users().messages().list(
        userId="me", maxResults=10, labelIds=["INBOX"]
    ).execute()

    messages = results.get("messages", [])
    email_summaries = []

    for message_metadata in messages:
        message = service.users().messages().get(
            userId="me", id=message_metadata["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()

        headers = message.get("payload", {}).get("headers", [])
        header_map = {header["name"]: header["value"] for header in headers}
        snippet = message.get("snippet", "")

        email_summaries.append({
            "from": header_map.get("From", "Unknown"),
            "subject": header_map.get("Subject", "(No Subject)"),
            "date": header_map.get("Date", "Unknown"),
            "snippet": snippet,
        })

    return email_summaries


def format_emails_for_prompt(email_summaries: list[dict]) -> str:
    """Format email summaries into a string for the Gemini prompt."""
    if not email_summaries:
        return "No recent emails found."

    lines = []
    for index, email in enumerate(email_summaries, 1):
        lines.append(
            f"{index}. From: {email['from']}\n"
            f"   Subject: {email['subject']}\n"
            f"   Date: {email['date']}\n"
            f"   Preview: {email['snippet']}"
        )
    return "\n\n".join(lines)
