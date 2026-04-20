"""ReportAgent — Synthesizes Drive files and Sheets data into project reports."""

import asyncio
from opscore.services import drive_service, sheets_service


class ReportAgent:
    """Agent responsible for generating reports from Drive and Sheets data."""

    name = "ReportAgent"

    async def fetch_and_report(self, credentials) -> dict:
        """Fetch Drive files and Sheets data concurrently, format for orchestrator.
        
        Returns dict with raw data and formatted prompt strings.
        """
        # Run both fetches concurrently
        drive_task = asyncio.to_thread(drive_service.fetch_recent_files, credentials)
        
        async def _safe_sheets(creds):
            try:
                return await asyncio.to_thread(
                    sheets_service.fetch_recent_spreadsheet_data, creds
                )
            except Exception:
                return None

        sheets_task = _safe_sheets(credentials)

        raw_files, raw_sheets = await asyncio.gather(drive_task, sheets_task)

        formatted_files = drive_service.format_files_for_prompt(raw_files)
        formatted_sheets = sheets_service.format_sheets_for_prompt(raw_sheets)

        return {
            "raw_drive": raw_files,
            "raw_sheets": raw_sheets,
            "formatted_drive": formatted_files,
            "formatted_sheets": formatted_sheets,
            "agent": self.name,
        }
