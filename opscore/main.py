"""FastAPI application entry point — wires all routes and serves the frontend."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from opscore.config import settings
from opscore.routes import auth, assistant

app = FastAPI(
    title="OpsCore — Smart Freelance Ops Assistant",
    description="AI assistant that reads Gmail, Calendar, and Drive to prioritize your day.",
    version="1.0.0",
)

# Session middleware for OAuth token storage (A6)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.APP_SECRET_KEY,
    max_age=3600,
)

# CORS restricted to localhost only (S6)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include route modules
app.include_router(auth.router)
app.include_router(assistant.router)

@app.get("/")
async def serve_frontend():
    """Return an API healthcheck; the Next.js frontend is served separately."""
    return {"message": "OpsCore AI API is actively serving."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("opscore.main:app", host="0.0.0.0", port=port, reload=False)
