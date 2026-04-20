"""Gmail API integration — fetches and summarizes the user's last 10 emails."""

import base64
from email.message import EmailMessage
from googleapiclient.discovery import build


def get_gmail_service(credentials):
    """Build an authorized Gmail API client."""
    return build("gmail", "v1", credentials=credentials)


def _extract_bodies(payload: dict) -> dict:
    """Recursively extract both text/plain and text/html from the MIME payload."""
    result = {"plain": "", "html": ""}

    mime = payload.get("mimeType", "")

    # Direct body data
    if 'data' in payload.get('body', {}):
        decoded = base64.urlsafe_b64decode(payload['body']['data']).decode("utf-8", errors="ignore")
        if mime == "text/html":
            result["html"] += decoded
        elif mime == "text/plain":
            result["plain"] += decoded
        else:
            result["plain"] += decoded  # fallback

    # Multipart — recurse into parts
    if 'parts' in payload:
        for part in payload['parts']:
            part_mime = part.get('mimeType', '')
            if part_mime == 'text/html':
                if 'data' in part.get('body', {}):
                    result["html"] += base64.urlsafe_b64decode(part['body']['data']).decode("utf-8", errors="ignore")
            elif part_mime == 'text/plain':
                if 'data' in part.get('body', {}):
                    result["plain"] += base64.urlsafe_b64decode(part['body']['data']).decode("utf-8", errors="ignore")
            elif 'parts' in part:
                sub = _extract_bodies(part)
                result["html"] += sub["html"]
                result["plain"] += sub["plain"]

    return result


def fetch_recent_emails(credentials) -> list[dict]:
    """Fetch the last 20 emails and return structured summaries."""
    service = get_gmail_service(credentials)
    results = service.users().messages().list(
        userId="me", maxResults=20, labelIds=["INBOX"]
    ).execute()

    messages = results.get("messages", [])
    email_summaries = []

    for message_metadata in messages:
        message = service.users().messages().get(
            userId="me", id=message_metadata["id"], format="full"
        ).execute()

        payload = message.get("payload", {})
        headers = payload.get("headers", [])
        header_map = {header["name"]: header["value"] for header in headers}
        snippet = message.get("snippet", "")

        bodies = _extract_bodies(payload)
        html_body = bodies["html"].strip()
        plain_body = bodies["plain"].strip()

        # 'body' = HTML preferred (for iframe display), 'body_plain' = text (for AI prompts)
        display_body = html_body or plain_body or snippet
        text_body = plain_body or snippet

        email_summaries.append({
            "from": header_map.get("From", "Unknown"),
            "subject": header_map.get("Subject", "(No Subject)"),
            "date": header_map.get("Date", "Unknown"),
            "snippet": snippet,
            "body": display_body,
            "body_plain": text_body,
        })

    return email_summaries


def send_email(credentials, to: str, subject: str, body: str):
    """Encode and physically dispatch an email via the Gmail API."""
    service = get_gmail_service(credentials)
    
    mime_message = EmailMessage()
    mime_message.set_content(body)
    mime_message['To'] = to
    mime_message['Subject'] = subject
    
    encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
    create_message = {'raw': encoded_message}
    
    return service.users().messages().send(userId="me", body=create_message).execute()


def format_emails_for_prompt(email_summaries: list[dict]) -> str:
    """Format email summaries into a string for the Gemini prompt."""
    if not email_summaries:
        return "No recent emails found."

    lines = []
    for index, email in enumerate(email_summaries, 1):
        # We cap the body size passed to the LLM context to prevent token blowouts on massive threads.
        truncated_body = email['body'][:1500] + ("..." if len(email['body']) > 1500 else "")
        lines.append(
            f"{index}. From: {email['from']}\n"
            f"   Subject: {email['subject']}\n"
            f"   Date: {email['date']}\n"
            f"   Body Preview: {truncated_body}"
        )
    return "\n\n".join(lines)
