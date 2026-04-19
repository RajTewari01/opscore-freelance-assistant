"""Pydantic models for all request/response shapes — used by every route (A5)."""

from pydantic import BaseModel, Field


class PriorityItem(BaseModel):
    """A single prioritized task returned by Gemini."""

    rank: int = Field(..., description="Priority rank (1 = highest)")
    task: str = Field(..., description="Description of the task")
    reason: str = Field(..., description="Why this task is urgent")
    urgency: str = Field(..., description="Urgency level: high, medium, or low")


class DraftedReply(BaseModel):
    """AI-drafted email reply for the most urgent message."""

    to: str = Field(..., description="Recipient email or name")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Full body text of the drafted reply")


class DeadlineAlert(BaseModel):
    """Alert for any deadline occurring within 24 hours."""

    exists: bool = Field(..., description="Whether a near-term deadline exists")
    event: str = Field(default="", description="Name of the deadline event")
    due: str = Field(default="", description="When it is due")
    action_needed: str = Field(default="", description="What the user should do")


class AnalysisResponse(BaseModel):
    """Complete response from the /analyze endpoint."""

    priority_queue: list[PriorityItem] = Field(
        ..., description="Top 3 prioritized tasks"
    )
    drafted_reply: DraftedReply = Field(
        ..., description="Drafted reply for the most urgent email"
    )
    deadline_alert: DeadlineAlert = Field(
        ..., description="Nearest deadline alert"
    )


class RegenerateRequest(BaseModel):
    """Request body for the /regenerate endpoint."""

    additional_context: str = Field(
        default="", description="Optional extra instructions for regeneration"
    )


class AuthStatus(BaseModel):
    """Current authentication status of the user."""

    is_authenticated: bool = Field(
        ..., description="Whether the user has a valid OAuth session"
    )
    user_name: str = Field(default="", description="Google display name")
    user_email: str = Field(default="", description="Google email address")
    user_picture: str = Field(default="", description="Google profile picture URL")


class ErrorResponse(BaseModel):
    """Standardized error response shown to the user (U8)."""

    error: str = Field(..., description="Human-readable error message")
    detail: str = Field(default="", description="Additional error context")
