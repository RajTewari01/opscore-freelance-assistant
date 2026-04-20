"""OAuth2 login and callback routes — tokens stored in session, never on disk (A6)."""

import os

# Allow OAuth2 over HTTP for local development (production must use HTTPS)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from itsdangerous import URLSafeTimedSerializer
from pydantic import BaseModel

from opscore.config import settings
from opscore.models.schemas import AuthStatus

router = APIRouter(prefix="/auth", tags=["auth"])

# Encrypted key serializer for HttpOnly cookie storage
_serializer = URLSafeTimedSerializer(settings.APP_SECRET_KEY)


def encrypt_key(api_key: str) -> str:
    """Encrypt an API key for secure cookie storage."""
    return _serializer.dumps(api_key)


def decrypt_key(token: str) -> str | None:
    """Decrypt an API key from cookie storage. Returns None if expired/invalid."""
    try:
        return _serializer.loads(token, max_age=28800)  # 8 hour expiry
    except Exception:
        return None


class SaveKeyRequest(BaseModel):
    provider: str
    api_key: str


@router.post("/settings/save-key")
async def save_api_key(body: SaveKeyRequest):
    """Store encrypted API key in HttpOnly cookie."""
    encrypted = encrypt_key(body.api_key)
    response = JSONResponse(content={"status": "saved"})
    response.set_cookie(
        key=f"key_{body.provider}",
        value=encrypted,
        httponly=True,
        secure=False,       # Set True in production with HTTPS
        samesite="lax",
        max_age=28800,      # 8 hours
    )
    return response


@router.post("/settings/clear-key")
async def clear_api_key(request: Request):
    """Remove API key cookie for a provider."""
    body = await request.json()
    provider = body.get("provider", "gemini")
    response = JSONResponse(content={"status": "cleared"})
    response.delete_cookie(key=f"key_{provider}")
    return response


def _build_flow() -> Flow:
    """Construct a Google OAuth2 flow from environment config."""
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=settings.SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    return flow


@router.get("/login")
async def login(request: Request):
    """Redirect the user to Google's OAuth2 consent screen."""
    flow = _build_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def callback(request: Request):
    """Handle the OAuth2 callback, exchange code for tokens, store in session."""
    flow = _build_flow()
    flow.fetch_token(authorization_response=str(request.url))

    credentials = flow.credentials
    request.session["token"] = credentials.token
    request.session["refresh_token"] = credentials.refresh_token
    request.session["token_uri"] = credentials.token_uri
    request.session["client_id"] = credentials.client_id
    request.session["client_secret"] = credentials.client_secret
    request.session["scopes"] = credentials.scopes

    # Fetch user profile info for the UI (U7)
    from googleapiclient.discovery import build

    oauth2_service = build("oauth2", "v2", credentials=credentials)
    user_info = oauth2_service.userinfo().get().execute()

    request.session["user_name"] = user_info.get("name", "")
    request.session["user_email"] = user_info.get("email", "")
    request.session["user_picture"] = user_info.get("picture", "")

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=frontend_url)


@router.get("/status", response_model=AuthStatus)
async def auth_status(request: Request) -> AuthStatus:
    """Return the current authentication status of the user."""
    token = request.session.get("token")
    if not token:
        return AuthStatus(
            is_authenticated=False,
            user_name="",
            user_email="",
            user_picture="",
        )
    return AuthStatus(
        is_authenticated=True,
        user_name=request.session.get("user_name", ""),
        user_email=request.session.get("user_email", ""),
        user_picture=request.session.get("user_picture", ""),
    )


@router.get("/logout")
async def logout(request: Request):
    """Clear the session and redirect to home."""
    request.session.clear()
    # Redirect back to the Next.js frontend (or fallback to /)
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return RedirectResponse(url=frontend_url)
