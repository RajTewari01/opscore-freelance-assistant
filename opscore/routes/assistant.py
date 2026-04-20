"""Assistant endpoints — /analyze, /regenerate, /history, /action orchestration."""

import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from opscore.models.schemas import (
    AnalysisResponse, ErrorResponse, RegenerateRequest,
    RawDataPayload, ActionRequest, ActionResponse,
)
from opscore.services import gmail_service, calendar_service, gemini_service, sheets_service
from opscore.agents.orchestrator import OpsOrchestrator
from opscore.database import get_db
from opscore.models.db_models import HistoricalAnalysis

router = APIRouter(prefix="/api", tags=["assistant"])

# Singleton orchestrator instance
orchestrator = OpsOrchestrator()


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


def _get_ai_config(request: Request) -> tuple[str | None, str | None]:
    """Extract AI provider and securely decrypt key from HttpOnly cookie (BYOK flow)."""
    from opscore.routes.auth import decrypt_key
    
    provider = request.headers.get("x-ai-provider", "gemini/gemini-2.0-flash")
    vendor = provider.split("/")[0] if "/" in provider else provider
    
    encrypted_key = request.cookies.get(f"key_{vendor}")
    api_key = decrypt_key(encrypted_key) if encrypted_key else None
    
    return provider, api_key


def _save_analysis_to_db(
    db: Session, user_email: str, provider: str,
    analysis_result: AnalysisResponse, raw_data: dict
):
    """Persist a successful analysis run to the database."""
    try:
        record = HistoricalAnalysis(
            user_email=user_email,
            provider=provider or "gemini/gemini-2.0-flash",
            priority_queue=json.dumps([p.model_dump() for p in analysis_result.priority_queue]),
            drafted_reply=json.dumps(analysis_result.drafted_reply.model_dump()),
            deadline_alert=json.dumps(analysis_result.deadline_alert.model_dump()),
            raw_emails=json.dumps(raw_data.get("emails", []), default=str),
            raw_calendar=json.dumps(raw_data.get("calendar", []), default=str),
            raw_drive=json.dumps(raw_data.get("drive", []), default=str),
            raw_sheets=json.dumps(raw_data.get("sheets"), default=str) if raw_data.get("sheets") else None,
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[DB] Failed to save analysis: {e}")


def _handle_ai_error(e: Exception) -> JSONResponse:
    """Centralized error handling for AI provider exceptions."""
    error_msg = repr(e)
    print(f"\n[DEBUG] AI Engine Error: {error_msg}\n")
    import traceback
    traceback.print_exc()

    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error="API Quota Exhausted: Your current Google API plan limit has been reached. Please wait and try again.",
                detail="429 RESOURCE_EXHAUSTED",
            ).model_dump(),
        )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="AI analysis failed. Please verify your API Key and try again.",
            detail=error_msg[:200],
        ).model_dump(),
    )


# ──────────────────────────────────────────────────────────────
# GET /api/fetch-data — Raw Data Fetch (NO AI call)
# ──────────────────────────────────────────────────────────────
@router.get("/fetch-data")
async def fetch_data(request: Request):
    """Fetch raw Gmail, Calendar, Drive, Sheets data WITHOUT any AI call.
    
    This is the primary data-loading endpoint called on login.
    It runs all 3 agents concurrently but skips the LLM entirely,
    preserving API tokens for on-demand actions.
    """
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
        # Run all agents concurrently — data fetch only, no LLM
        import asyncio
        from opscore.agents.email_agent import EmailAgent
        from opscore.agents.calendar_agent import CalendarAgent
        from opscore.agents.report_agent import ReportAgent

        email_agent = EmailAgent()
        calendar_agent = CalendarAgent()
        report_agent = ReportAgent()

        email_result, calendar_result, report_result = await asyncio.gather(
            email_agent.fetch_and_classify(credentials),
            calendar_agent.fetch_and_analyze(credentials),
            report_agent.fetch_and_report(credentials),
        )

        return {
            "emails": email_result["raw"],
            "calendar": calendar_result["raw"],
            "drive": report_result["raw_drive"],
            "sheets": report_result["raw_sheets"],
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Failed to fetch data from Google services.",
                detail=str(e)[:200],
            ).model_dump(),
        )


# ──────────────────────────────────────────────────────────────
# POST /api/analyze — Multi-Agent Orchestrator Pipeline
# ──────────────────────────────────────────────────────────────
@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(request: Request, db: Session = Depends(get_db)):
    """Run the full multi-agent pipeline: fetch all sources concurrently, analyze with LLM, persist to DB."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(
            status_code=401,
            content=ErrorResponse(
                error="Not authenticated",
                detail="Please sign in with Google first.",
            ).model_dump(),
        )

    ai_provider, ai_key = _get_ai_config(request)

    # Run the orchestrator pipeline (all 3 agents concurrently)
    try:
        analysis_result, raw_data = await orchestrator.run_pipeline(
            credentials, provider=ai_provider, api_key=ai_key
        )
    except Exception as e:
        return _handle_ai_error(e)

    # Inject raw data onto the response for the frontend
    analysis_result.raw_data = RawDataPayload(
        emails=raw_data["emails"],
        calendar=raw_data["calendar"],
        drive=raw_data["drive"],
        sheets=raw_data["sheets"],
    )

    # Persist to database
    user_email = request.session.get("user_email", "anonymous")
    _save_analysis_to_db(db, user_email, ai_provider, analysis_result, raw_data)

    return analysis_result


# ──────────────────────────────────────────────────────────────
# POST /api/regenerate — Re-run with additional context
# ──────────────────────────────────────────────────────────────
@router.post("/regenerate", response_model=AnalysisResponse)
async def regenerate(request: Request, body: RegenerateRequest, db: Session = Depends(get_db)):
    """Re-run analysis with optional additional context from the user."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(status_code=401, content=ErrorResponse(error="Not authenticated").model_dump())

    ai_provider, ai_key = _get_ai_config(request)

    try:
        analysis_result, raw_data = await orchestrator.run_pipeline(
            credentials, provider=ai_provider, api_key=ai_key
        )
    except Exception as e:
        return _handle_ai_error(e)

    analysis_result.raw_data = RawDataPayload(
        emails=raw_data["emails"],
        calendar=raw_data["calendar"],
        drive=raw_data["drive"],
        sheets=raw_data["sheets"],
    )

    user_email = request.session.get("user_email", "anonymous")
    _save_analysis_to_db(db, user_email, ai_provider, analysis_result, raw_data)

    return analysis_result


# ──────────────────────────────────────────────────────────────
# GET /api/history — Fetch past analysis runs from DB
# ──────────────────────────────────────────────────────────────
@router.get("/history")
async def get_history(request: Request, db: Session = Depends(get_db)):
    """Return the last 20 analysis runs for the authenticated user."""
    user_email = request.session.get("user_email")
    if not user_email:
        return JSONResponse(status_code=401, content=ErrorResponse(error="Not authenticated").model_dump())

    records = (
        db.query(HistoricalAnalysis)
        .filter(HistoricalAnalysis.user_email == user_email)
        .order_by(HistoricalAnalysis.created_at.desc())
        .limit(20)
        .all()
    )
    return [r.to_dict() for r in records]


# ──────────────────────────────────────────────────────────────
# POST /api/action — Micro-actions (draft, schedule, graphify, etc.)
# ──────────────────────────────────────────────────────────────
@router.post("/action", response_model=ActionResponse)
async def perform_action(request: Request, body: ActionRequest):
    """Executes a highly granular action on a specific focused item."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(status_code=401, content=ErrorResponse(error="Not authenticated").model_dump())

    context_str = json.dumps(body.context_item, indent=2)
    ai_provider, ai_key = _get_ai_config(request)

    try:
        if body.action_type == "schedule":
            prompt = f"Based on this context:\n{context_str}\n\nAnd user instruction: {body.additional_context}\n\nCreate a JSON payload for a Google Calendar event. Format exactly as: {{\"summary\": \"...\", \"start\": {{\"dateTime\": \"2026-04-19T10:00:00Z\"}}, \"end\": {{\"dateTime\": \"2026-04-19T11:00:00Z\"}}}}"
            response_json = gemini_service.execute_action_prompt(prompt, expect_json=True, provider=ai_provider, api_key=ai_key)
            payload = json.loads(response_json)
            from opscore.services import calendar_service
            result = calendar_service.insert_event(credentials, payload)
            return ActionResponse(status="success", result="Event scheduled successfully!")

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


@router.post("/analytics")
async def run_analytics(request: Request):
    """Single AI call to analyze all workspace data and return priority rankings + report."""
    credentials = _get_credentials(request)
    if not credentials:
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})

    ai_provider, ai_key = _get_ai_config(request)

    try:
        body = await request.json()
        emails = body.get("emails", [])
        calendar = body.get("calendar", [])
        drive = body.get("drive", [])
        limit = body.get("limit", 5)

        # Slice data to respect the user's limit
        emails_limited = emails[:limit]
        calendar_limited = calendar[:limit]
        drive_limited = drive[:limit]

        # Build a compact context string
        context_parts = []

        if emails_limited:
            context_parts.append("=== EMAILS ===")
            for i, e in enumerate(emails_limited, 1):
                body_preview = (e.get("body_plain") or e.get("snippet", ""))[:300]
                context_parts.append(
                    f"[Email {i}] From: {e.get('from','?')} | Subject: {e.get('subject','?')} | Date: {e.get('date','?')}\n{body_preview}"
                )

        if calendar_limited:
            context_parts.append("\n=== CALENDAR ===")
            for i, ev in enumerate(calendar_limited, 1):
                context_parts.append(
                    f"[Event {i}] {ev.get('summary','?')} | Start: {ev.get('start','?')} | End: {ev.get('end','?')}"
                )

        if drive_limited:
            context_parts.append("\n=== DRIVE FILES ===")
            for i, f in enumerate(drive_limited, 1):
                context_parts.append(
                    f"[File {i}] {f.get('name','?')} | Type: {f.get('mimeType','?')} | Modified: {f.get('modifiedTime','?')}"
                )

        context_str = "\n".join(context_parts)

        prompt = f"""You are a freelancer's AI operations analyst. Analyze the following workspace data and produce TWO things:

1. **priority_items**: A JSON array of actionable items ranked by urgency. Each item has:
   - "rank" (integer, 1 = most urgent)
   - "urgency" ("high", "medium", or "low")
   - "title" (short title of the task)
   - "source" ("email" or "calendar" or "drive")
   - "source_index" (0-based index in the original array)
   - "reason" (why this is urgent — 1 sentence)

2. **report**: A markdown report (3-5 paragraphs) summarizing:
   - Overall workload assessment
   - Critical deadlines or urgent items
   - Recommended priority order for today
   - Any risks or items that need immediate attention

Respond ONLY with a JSON object in this exact format:
{{
  "priority_items": [...],
  "report": "markdown string"
}}

=== WORKSPACE DATA ===
{context_str}
"""

        response_text = gemini_service.execute_action_prompt(
            prompt, expect_json=True, provider=ai_provider, api_key=ai_key
        )

        result = json.loads(response_text)
        return JSONResponse(content=result)

    except json.JSONDecodeError:
        return JSONResponse(
            status_code=500,
            content={"error": "AI returned invalid JSON. Please try again."}
        )
    except Exception as e:
        return _handle_ai_error(e)
