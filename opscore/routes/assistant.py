"""Assistant endpoints — /analyze and /regenerate orchestration (A1, A2)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.oauth2.credentials import Credentials

from opscore.models.schemas import AnalysisResponse, ErrorResponse, RegenerateRequest
from opscore.services import gmail_service, calendar_service, drive_service, gemini_service

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
            status_code=502,
            content=ErrorResponse(
                error="Could not fetch Gmail data. Check your connection and try again.",
                detail="Gmail API request failed.",
            ).model_dump(),
        )

    try:
        calendar_events = calendar_service.fetch_todays_events(credentials)
    except Exception:
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error="Could not fetch Calendar data. Check your connection and try again.",
                detail="Calendar API request failed.",
            ).model_dump(),
        )

    try:
        drive_files = drive_service.fetch_recent_files(credentials)
    except Exception:
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error="Could not fetch Drive data. Check your connection and try again.",
                detail="Drive API request failed.",
            ).model_dump(),
        )

    # Step 2: Format all data into prompt strings
    formatted_emails = gmail_service.format_emails_for_prompt(email_summaries)
    formatted_events = calendar_service.format_events_for_prompt(calendar_events)
    formatted_files = drive_service.format_files_for_prompt(drive_files)

    # Step 3: Build a single context prompt (A2)
    context_prompt = gemini_service.build_prompt(
        email_summaries=formatted_emails,
        calendar_events=formatted_events,
        drive_files=formatted_files,
    )

    # Step 4: Make one Gemini call and return the parsed response
    try:
        analysis_result = gemini_service.analyze_context(context_prompt)
    except Exception:
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error="AI analysis failed. Please try again.",
                detail="Gemini API request or response parsing failed.",
            ).model_dump(),
        )

    return analysis_result


@router.post("/regenerate", response_model=AnalysisResponse)
async def regenerate(request: Request, body: RegenerateRequest):
    """Re-run analysis with optional additional context from the user."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(
                error="Not authenticated",
                detail="Please sign in with Google first.",
            ).model_dump(),
        )

    try:
        email_summaries = gmail_service.fetch_recent_emails(credentials)
        calendar_events = calendar_service.fetch_todays_events(credentials)
        drive_files = drive_service.fetch_recent_files(credentials)
    except Exception:
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error="Could not fetch your data. Check your connection and try again.",
                detail="One or more Google API requests failed.",
            ).model_dump(),
        )

    formatted_emails = gmail_service.format_emails_for_prompt(email_summaries)
    formatted_events = calendar_service.format_events_for_prompt(calendar_events)
    formatted_files = drive_service.format_files_for_prompt(drive_files)

    context_prompt = gemini_service.build_prompt(
        email_summaries=formatted_emails,
        calendar_events=formatted_events,
        drive_files=formatted_files,
    )

    if body.additional_context:
        context_prompt += f"\n\nAdditional user instructions: {body.additional_context}"

    try:
        analysis_result = gemini_service.analyze_context(context_prompt)
    except Exception:
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                error="AI analysis failed. Please try again.",
                detail="Gemini API request or response parsing failed.",
            ).model_dump(),
        )

    return analysis_result
