"""Google Sheets API integration — fetches data from the most recent spreadsheet."""

from googleapiclient.discovery import build

def get_drive_service(credentials):
    """Build an authorized Google Drive API client."""
    return build("drive", "v3", credentials=credentials)


def get_sheets_service(credentials):
    """Build an authorized Google Sheets API client."""
    return build("sheets", "v4", credentials=credentials)


def fetch_recent_spreadsheet_data(credentials) -> dict | None:
    """Finds the most recently modified spreadsheet and reads its first 15 rows."""
    drive_service = get_drive_service(credentials)
    
    # 1. Find the latest spreadsheet
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.spreadsheet'",
        pageSize=1,
        orderBy="modifiedTime desc",
        fields="files(id, name)"
    ).execute()
    
    files = results.get("files", [])
    if not files:
        return None
        
    latest_sheet = files[0]
    sheet_id = latest_sheet["id"]
    sheet_name = latest_sheet["name"]
    
    # 2. Read data from the spreadsheet
    sheets_service = get_sheets_service(credentials)
    
    try:
        # We fetch up to columns A-F and 15 rows to keep context sizes reasonable
        sheet = sheets_service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range="A1:F15").execute()
        values = result.get("values", [])
        
        return {
            "name": sheet_name,
            "id": sheet_id,
            "data": values
        }
    except Exception as e:
        print(f"Error fetching sheets: {e}")
        return None


def format_sheets_for_prompt(sheet_data: dict | None) -> str:
    """Format the spreadsheet data into a string for the Gemini prompt."""
    if not sheet_data:
        return "No recent spreadsheet data found."
        
    lines = [f"Spreadsheet Name: {sheet_data['name']}"]
    lines.append("Data (First 15 rows):")
    
    if not sheet_data["data"]:
        lines.append("  (Spreadsheet is empty)")
    else:
        for row in sheet_data["data"]:
            lines.append("  |  " + "  |  ".join(row))
            
    return "\n".join(lines)
