"""OAuth2 login and callback routes — tokens stored in session, never on disk (A6)."""

import os

# Allow OAuth2 over HTTP for local development (production must use HTTPS)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from opscore.config import settings
from opscore.models.schemas import AuthStatus

router = APIRouter(prefix="/auth", tags=["auth"])


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
