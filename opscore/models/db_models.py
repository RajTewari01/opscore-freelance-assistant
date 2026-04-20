"""SQLAlchemy ORM models for persistent storage."""

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from opscore.database import Base


class HistoricalAnalysis(Base):
    """Stores every successful AI analysis run for history & caching."""
    __tablename__ = "historical_analyses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_email = Column(String(255), index=True, nullable=False)
    provider = Column(String(100), nullable=False, default="gemini/gemini-2.0-flash")
    priority_queue = Column(Text, nullable=False)       # JSON string
    drafted_reply = Column(Text, nullable=False)         # JSON string
    deadline_alert = Column(Text, nullable=False)        # JSON string
    raw_emails = Column(Text, default="[]")              # JSON string
    raw_calendar = Column(Text, default="[]")            # JSON string
    raw_drive = Column(Text, default="[]")               # JSON string
    raw_sheets = Column(Text, default=None, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "id": self.id,
            "user_email": self.user_email,
            "provider": self.provider,
            "priority_queue": json.loads(self.priority_queue),
            "drafted_reply": json.loads(self.drafted_reply),
            "deadline_alert": json.loads(self.deadline_alert),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
