"""Environment configuration loader — all secrets loaded from .env file."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded exclusively from environment variables."""

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/callback"
    )
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    APP_SECRET_KEY: str = os.getenv("APP_SECRET_KEY", "change-me-in-production")

    SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/drive.metadata.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]


settings = Settings()
