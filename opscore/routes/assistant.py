"""Assistant endpoints — /analyze and /regenerate orchestration (A1, A2)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.oauth2.credentials import Credentials

from opscore.models.schemas import AnalysisResponse, ErrorResponse, RegenerateRequest, RawDataPayload
from opscore.services import gmail_service, calendar_service, drive_service, gemini_service, sheets_service

router = APIRouter(prefix="/api", tags=["assistant"])


def _get_credentials(request: Request) -> Credentials | None:
    """Reconstruct Google credentials from session data."""
    token = request.session.get("token")
    if not token:
        return None
    return Credentials(
        token=token,
        refresh_token=request.session.get("refresh_token"),
        token_uri=request.session.get("token_uri"),
        client_id=request.session.get("client_id"),
        client_secret=request.session.get("client_secret"),
        scopes=request.session.get("scopes"),
    )


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: Request):
    """Fetch Gmail + Calendar + Drive data, send one Gemini call, return analysis."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(
                error="Not authenticated",
                detail="Please sign in with Google first.",
            ).model_dump(),
        )

    # Step 1: Fetch all data from the three Google services
    try:
        email_summaries = gmail_service.fetch_recent_emails(credentials)
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Could not fetch Gmail data. Check your connection and try again.",
                detail="Gmail API request failed.",
            ).model_dump(),
        )

    try:
        calendar_events = calendar_service.fetch_todays_events(credentials)
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Could not fetch Calendar data. Check your connection and try again.",
                detail="Calendar API request failed.",
            ).model_dump(),
        )

    try:
        drive_files = drive_service.fetch_recent_files(credentials)
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Could not fetch Drive data. Check your connection and try again.",
                detail="Drive API request failed.",
            ).model_dump(),
        )

    try:
        sheet_data = sheets_service.fetch_recent_spreadsheet_data(credentials)
    except Exception:
        sheet_data = None

    # Step 2: Format all data into prompt strings
    formatted_emails = gmail_service.format_emails_for_prompt(email_summaries)
    formatted_events = calendar_service.format_events_for_prompt(calendar_events)
    formatted_files = drive_service.format_files_for_prompt(drive_files)
    formatted_sheet = sheets_service.format_sheets_for_prompt(sheet_data)

    # Step 3: Build a single context prompt (A2)
    context_prompt = gemini_service.build_prompt(
        email_summaries=formatted_emails,
        calendar_events=formatted_events,
        drive_files=formatted_files,
    )
    context_prompt += f"\n\nGoogle Sheets Data:\n{formatted_sheet}"

    # Step 4: Make one Model call and return the parsed response
    ai_provider = request.headers.get("x-ai-provider")
    ai_key = request.headers.get("x-ai-key")
    try:
        analysis_result = gemini_service.analyze_context(context_prompt, provider=ai_provider, api_key=ai_key)
    except Exception as e:
        print(f"\n[DEBUG] AI Engine Error: {repr(e)}\n")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="AI analysis failed. Please check your API Key and try again.",
                detail="Provider API request or response parsing failed.",
            ).model_dump(),
        )

    # Step 5: Inject Raw Data payload directly onto the validated AI model
    analysis_result.raw_data = RawDataPayload(
        emails=email_summaries,
        calendar=calendar_events,
        drive=drive_files,
        sheets=sheet_data
    )

    return analysis_result


@router.post("/regenerate", response_model=AnalysisResponse)
async def regenerate(request: Request, body: RegenerateRequest):
    """Re-run analysis with optional additional context from the user."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(status_code=401, content=ErrorResponse(error="Not authenticated").model_dump())

    try:
        email_summaries = gmail_service.fetch_recent_emails(credentials)
        calendar_events = calendar_service.fetch_todays_events(credentials)
        drive_files = drive_service.fetch_recent_files(credentials)
        try:
            sheet_data = sheets_service.fetch_recent_spreadsheet_data(credentials)
        except Exception:
            sheet_data = None
    except Exception:
        return JSONResponse(status_code=500, content=ErrorResponse(error="Fetch failed").model_dump())

    formatted_emails = gmail_service.format_emails_for_prompt(email_summaries)
    formatted_events = calendar_service.format_events_for_prompt(calendar_events)
    formatted_files = drive_service.format_files_for_prompt(drive_files)
    formatted_sheet = sheets_service.format_sheets_for_prompt(sheet_data)

    context_prompt = gemini_service.build_prompt(formatted_emails, formatted_events, formatted_files)
    context_prompt += f"\n\nGoogle Sheets Data:\n{formatted_sheet}"

    if body.additional_context:
        context_prompt += f"\n\nAdditional user instructions: {body.additional_context}"

    ai_provider = request.headers.get("x-ai-provider")
    ai_key = request.headers.get("x-ai-key")
    try:
        analysis_result = gemini_service.analyze_context(context_prompt, provider=ai_provider, api_key=ai_key)
    except Exception:
        return JSONResponse(status_code=500, content=ErrorResponse(error="AI computation failed").model_dump())

    analysis_result.raw_data = RawDataPayload(emails=email_summaries, calendar=calendar_events, drive=drive_files, sheets=sheet_data)
    return analysis_result


from opscore.models.schemas import ActionRequest, ActionResponse
import json

@router.post("/action", response_model=ActionResponse)
async def perform_action(request: Request, body: ActionRequest):
    """Executes a highly granular action on a specific focused item."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(status_code=401, content=ErrorResponse(error="Not authenticated").model_dump())

    context_str = json.dumps(body.context_item, indent=2)
    ai_provider = request.headers.get("x-ai-provider")
    ai_key = request.headers.get("x-ai-key")

    try:
        if body.action_type == "schedule":
            prompt = f"Based on this context:\n{context_str}\n\nAnd user instruction: {body.additional_context}\n\nCreate a JSON payload for a Google Calendar event. Format exactly as: {{\"summary\": \"...\", \"start\": {{\"dateTime\": \"2026-04-19T10:00:00Z\"}}, \"end\": {{\"dateTime\": \"2026-04-19T11:00:00Z\"}}}}"
            response_json = gemini_service.execute_action_prompt(prompt, expect_json=True, provider=ai_provider, api_key=ai_key)
            payload = json.loads(response_json)
            result = calendar_service.insert_event(credentials, payload)
            return ActionResponse(status="success", result=f"Event scheduled successfully!")

        elif body.action_type == "graphify":
            prompt = f"Transform this raw sheet data into a JSON array for Recharts.\nData:\n{context_str}\n\nUser Instruction: {body.additional_context}\nRespond ONLY with the JSON array."
            response_json = gemini_service.execute_action_prompt(prompt, expect_json=True, provider=ai_provider, api_key=ai_key)
            return ActionResponse(status="success", result=json.loads(response_json))

        elif body.action_type == "draft":
            prompt = f"Draft an email reply.\nContext email:\n{context_str}\n\nUser Instruction: {body.additional_context}\nRespond ONLY with a JSON object: {{\"subject\": \"...\", \"body\": \"...\", \"to\": \"...\"}}"
            response_json = gemini_service.execute_action_prompt(prompt, expect_json=True, provider=ai_provider, api_key=ai_key)
            return ActionResponse(status="success", result=json.loads(response_json))

        elif body.action_type == "dispatch":
            payload = body.context_item
            from opscore.services.gmail_service import send_email
            result = send_email(credentials, to=payload["to"], subject=payload.get("subject", "Update from OpsCore"), body=payload["body"])
            return ActionResponse(status="success", result="Email Dispatched to Server successfully!")

        elif body.action_type == "summarize":
            prompt = f"Summarize this item thoroughly.\nContext:\n{context_str}\nUser Instruction: {body.additional_context}"
            response_text = gemini_service.execute_action_prompt(prompt, expect_json=False, provider=ai_provider, api_key=ai_key)
            return ActionResponse(status="success", result=response_text)

        return ActionResponse(status="error", result="Unknown action type")

    except Exception as e:
        return ActionResponse(status="error", result=f"Action failed: {str(e)}")
