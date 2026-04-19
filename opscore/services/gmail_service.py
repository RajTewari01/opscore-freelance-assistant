"""Gmail API integration — fetches and summarizes the user's last 10 emails."""

import base64
from email.message import EmailMessage
from googleapiclient.discovery import build


def get_gmail_service(credentials):
    """Build an authorized Gmail API client."""
    return build("gmail", "v1", credentials=credentials)


def _get_email_body(payload: dict) -> str:
    """Recursively extract plain text from the MIME payload."""
    body_text = ""
    # If the payload itself has the body
    if 'data' in payload.get('body', {}):
        body_text += base64.urlsafe_b64decode(payload['body']['data']).decode("utf-8", errors="ignore")
    # If it is a multipart payload
    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain':
                if 'data' in part.get('body', {}):
                    body_text += base64.urlsafe_b64decode(part['body']['data']).decode("utf-8", errors="ignore")
            elif 'parts' in part:
                 body_text += _get_email_body(part) # Recurse
    return body_text


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
        
        full_body = _get_email_body(payload).strip()
        if not full_body:
             full_body = snippet # fallback

        email_summaries.append({
            "from": header_map.get("From", "Unknown"),
            "subject": header_map.get("Subject", "(No Subject)"),
            "date": header_map.get("Date", "Unknown"),
            "snippet": snippet,
            "body": full_body,
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
