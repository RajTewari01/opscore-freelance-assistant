"""Google Drive API integration — fetches the 5 most recently modified files."""

from googleapiclient.discovery import build


def get_drive_service(credentials):
    """Build an authorized Google Drive API client."""
    return build("drive", "v3", credentials=credentials)


def fetch_recent_files(credentials) -> list[dict]:
    """Fetch the 5 most recently modified Drive files (metadata only)."""
    service = get_drive_service(credentials)

    results = service.files().list(
        pageSize=5,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime, owners)",
    ).execute()

    raw_files = results.get("files", [])
    drive_files = []

    for file_entry in raw_files:
        owners = file_entry.get("owners", [])
        owner_name = owners[0].get("displayName", "Unknown") if owners else "Unknown"
        drive_files.append({
            "name": file_entry.get("name", "Untitled"),
            "mime_type": file_entry.get("mimeType", "Unknown"),
            "modified_time": file_entry.get("modifiedTime", "Unknown"),
            "owner": owner_name,
        })

    return drive_files


def format_files_for_prompt(drive_files: list[dict]) -> str:
    """Format Drive file metadata into a string for the Gemini prompt."""
    if not drive_files:
        return "No recent Drive files found."

    lines = []
    for index, file_entry in enumerate(drive_files, 1):
        lines.append(
            f"{index}. {file_entry['name']}\n"
            f"   Type: {file_entry['mime_type']}\n"
            f"   Last modified: {file_entry['modified_time']}\n"
            f"   Owner: {file_entry['owner']}"
        )
    return "\n\n".join(lines)
