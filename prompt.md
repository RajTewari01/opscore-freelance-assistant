# PROMPT.md — Smart Freelance Ops Assistant
## Build Instructions for Google Antigravity AI
### Vertical: Business / Freelance Operations
### Author Context: Solo developer running an async international agency

---

## ⚡ MASTER DIRECTIVE

You are building a **complete, production-ready, submission-ready web application** from scratch in a single session. Do not ask clarifying questions. Do not stop mid-build. Do not produce placeholder code. Every file you create must be functional, connected, and runnable. The final output must pass a live demo in front of judges with zero manual fixes.

---

## 🧱 WHAT YOU ARE BUILDING

**App Name:** `OpsCore` — Smart Freelance Operations Assistant

**One-line pitch:** An AI assistant that reads your Gmail, Google Calendar, and Google Drive to tell you exactly what to work on next — and drafts the client reply for you.

**Target user:** A solo developer / freelancer managing async clients across multiple timezones.

**Core user flow:**
1. User lands on the app → clicks "Analyze My Day"
2. App fetches last 10 emails (Gmail), today's calendar events, and recent Drive files
3. Bundles all context into a single Gemini API call
4. Returns a **Priority Queue** (top 3 tasks), a **Drafted Reply** for the most urgent email, and a **Deadline Alert** if anything is due within 24 hours
5. User can click "Regenerate" or "Copy Reply" — that's the full loop

---

## 📐 TECH STACK (DO NOT DEVIATE)

```
Backend  : Python 3.11+ / FastAPI
Frontend : Single-file React (index.html with CDN React + Tailwind)
AI       : Google Gemini 1.5 Flash API (gemini-1.5-flash)
Auth     : Google OAuth 2.0 (via google-auth + google-auth-oauthlib)
APIs     : Gmail API, Google Calendar API, Google Drive API, Gemini API
Env      : python-dotenv for all secrets
Testing  : pytest + unittest.mock (minimum 5 tests)
Deploy   : Runs locally with `uvicorn main:app --reload`
```

---

## 🗂️ REQUIRED FILE STRUCTURE

Generate every file listed below. No file is optional.

```
opscore/
├── main.py                  # FastAPI app entry point
├── config.py                # Environment config loader
├── requirements.txt         # All dependencies pinned
├── .env.example             # Template (no real secrets)
├── .gitignore               # Excludes .env, __pycache__, credentials
│
├── services/
│   ├── __init__.py
│   ├── gmail_service.py     # Gmail API integration
│   ├── calendar_service.py  # Google Calendar API integration
│   ├── drive_service.py     # Google Drive API integration
│   └── gemini_service.py    # Gemini API prompt + response parser
│
├── routes/
│   ├── __init__.py
│   ├── auth.py              # OAuth2 login + callback routes
│   └── assistant.py         # /analyze and /regenerate endpoints
│
├── models/
│   ├── __init__.py
│   └── schemas.py           # Pydantic models for all request/response shapes
│
├── static/
│   └── index.html           # Full frontend (React + Tailwind via CDN)
│
├── tests/
│   ├── __init__.py
│   ├── test_gmail.py
│   ├── test_calendar.py
│   ├── test_gemini.py
│   └── test_routes.py
│
└── README.md                # Full project documentation
```

---

# 🔷 4D RULES

These are non-negotiable constraints applied across all 4 dimensions of the build. Violating any rule disqualifies the output.

---

## DIMENSION 1 — ARCHITECTURE RULES
*How the system is structured and connected*

**[A1] Separation of concerns is absolute.**
Each service file (gmail, calendar, drive, gemini) handles ONLY its own API. No service imports another service. All orchestration happens in `routes/assistant.py`.

**[A2] Single Gemini call per analysis.**
Do NOT make 4 separate Gemini calls. Collect all data first (Gmail + Calendar + Drive), build one rich context string, make one `gemini_service.analyze_context(context)` call. This is the core efficiency signal.

**[A3] Gemini prompt must be structured, not freeform.**
The prompt sent to Gemini must follow this exact template:

```
You are an operations assistant for a solo freelance developer.

## Current Context
### Emails (last 10, newest first):
{email_summaries}

### Today's Calendar Events:
{calendar_events}

### Recent Drive Files (last 5):
{drive_files}

## Your Task
Respond ONLY in the following JSON format. No markdown, no explanation outside the JSON.

{
  "priority_queue": [
    {"rank": 1, "task": "...", "reason": "...", "urgency": "high|medium|low"},
    {"rank": 2, "task": "...", "reason": "...", "urgency": "high|medium|low"},
    {"rank": 3, "task": "...", "reason": "...", "urgency": "high|medium|low"}
  ],
  "drafted_reply": {
    "to": "...",
    "subject": "Re: ...",
    "body": "..."
  },
  "deadline_alert": {
    "exists": true,
    "event": "...",
    "due": "...",
    "action_needed": "..."
  }
}
```

**[A4] FastAPI must serve the frontend.**
Mount `/static` using `StaticFiles`. The root route `/` returns `index.html`. No separate frontend server.

**[A5] All routes return typed Pydantic responses.**
Define `AnalysisResponse`, `RegenerateRequest`, `AuthStatus` in `models/schemas.py`. Every route uses these — no raw dicts returned from endpoints.

**[A6] OAuth tokens must be stored in the session, not in files.**
Use `itsdangerous` or FastAPI's session middleware. Never write `token.json` to disk in production flow.

---

## DIMENSION 2 — SECURITY RULES
*How the system protects data and credentials*

**[S1] Zero hardcoded secrets.**
Every API key, client ID, client secret, and redirect URI lives in `.env`. Config is loaded exclusively via `config.py` using `python-dotenv`. If a secret appears in any source file, the build fails.

**[S2] `.env.example` must exist with placeholder values.**
```
GOOGLE_CLIENT_ID=your-client-id-here
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
GEMINI_API_KEY=your-gemini-api-key-here
APP_SECRET_KEY=your-random-secret-key-here
```

**[S3] `.gitignore` must exclude sensitive files.**
```
.env
credentials.json
token.json
__pycache__/
*.pyc
.pytest_cache/
```

**[S4] OAuth scopes must be minimal.**
Request only what is needed:
```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]
```
Never request write scopes for data you only read.

**[S5] All user data is ephemeral.**
No email content, calendar data, or Drive metadata is persisted to any database or file. Every analysis call fetches fresh data and discards it after the response is returned.

**[S6] CORS must be restricted.**
In `main.py`, set `allow_origins=["http://localhost:8000"]` — not `["*"]`.

---

## DIMENSION 3 — UX & ACCESSIBILITY RULES
*How the interface looks and behaves*

**[U1] The UI must be a single `index.html` file.**
Use React 18 via CDN (`unpkg.com`). Use Tailwind CSS via CDN. No build step, no npm, no bundler.

**[U2] Three-panel layout on desktop, stacked on mobile.**
```
[ Priority Queue ]  [ Drafted Reply ]  [ Deadline Alert ]
```
On mobile (`< 768px`), stack vertically. Use Tailwind's `md:grid-cols-3` pattern.

**[U3] Loading state is mandatory.**
While Gemini is processing, show a spinner with the text "Analyzing your day..." — disable the "Analyze" button. Do not leave the user staring at a blank screen.

**[U4] "Copy Reply" button must work.**
Use `navigator.clipboard.writeText()`. Show a brief "Copied!" confirmation for 2 seconds.

**[U5] Urgency must be color-coded.**
```
high   → red badge   (#ef4444)
medium → yellow badge (#f59e0b)
low    → green badge  (#22c55e)
```

**[U6] ARIA labels on all interactive elements.**
Every button must have `aria-label`. Input fields must have `htmlFor` labels. Color is never the ONLY indicator of state — pair color with text/icon.

**[U7] Auth state must be visible.**
Show the logged-in user's Google profile picture and name in the top-right corner after login. Show a "Sign in with Google" button when logged out.

**[U8] Error states must be human-readable.**
If any API call fails, show: `"Could not fetch [Gmail/Calendar/Drive] data. Check your connection and try again."` — never expose raw error objects to the UI.

---

## DIMENSION 4 — QUALITY & SUBMISSION RULES
*How the code is written and how the project is packaged*

**[Q1] `requirements.txt` must be pinned and complete.**
```
fastapi==0.111.0
uvicorn==0.29.0
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0
google-api-python-client==2.127.0
google-generativeai==0.5.4
python-dotenv==1.0.1
itsdangerous==2.2.0
starlette==0.37.2
pydantic==2.7.1
pytest==8.2.0
httpx==0.27.0
```

**[Q2] Minimum 5 tests must pass.**
Cover:
- `test_gmail.py` — mock Gmail API, assert email summaries are extracted correctly
- `test_calendar.py` — mock Calendar API, assert today's events are returned
- `test_gemini.py` — mock Gemini response, assert JSON is parsed into correct Pydantic model
- `test_routes.py` — test `/analyze` returns 401 when not authenticated, test `/analyze` returns valid `AnalysisResponse` with mocked services

**[Q3] README.md must contain all 5 sections.**

```markdown
# OpsCore — Smart Freelance Ops Assistant

## Chosen Vertical
Business / Freelance Operations

## Problem Statement
[2-3 sentences on the real problem]

## Approach and Logic
[How the 4 Google services connect through Gemini]

## How to Run
1. Clone the repo
2. Copy `.env.example` to `.env` and fill in keys
3. `pip install -r requirements.txt`
4. `uvicorn main:app --reload`
5. Open `http://localhost:8000`

## Assumptions
[List any assumptions made during build]
```

**[Q4] Repo size must stay under 1 MB.**
Never commit: `node_modules`, `.env`, `venv/`, `__pycache__/`, any model files, any image files over 100KB.

**[Q5] Single branch only.**
All commits go to `main`. No feature branches, no dev branches.

**[Q6] Commit at logical checkpoints.**
Suggested commit messages:
```
feat: project scaffold and config
feat: google oauth2 flow
feat: gmail, calendar, drive service integrations
feat: gemini orchestration layer
feat: fastapi routes and pydantic schemas
feat: frontend react ui
test: unit tests for all services
docs: readme and env example
```

**[Q7] Code must be readable.**
- Max function length: 40 lines
- Every function has a one-line docstring
- No abbreviations in variable names (`em` → `email`, `cal` → `calendar_event`)
- No commented-out code in final submission

---

## 🚀 BUILD ORDER

Follow this exact sequence. Do not skip ahead.

```
1. Generate file structure (all empty files with correct imports)
2. config.py + .env.example + .gitignore
3. models/schemas.py (all Pydantic models)
4. services/gmail_service.py
5. services/calendar_service.py
6. services/drive_service.py
7. services/gemini_service.py (with exact prompt template from A3)
8. routes/auth.py
9. routes/assistant.py
10. main.py (wire everything together)
11. static/index.html (full React UI)
12. tests/ (all 4 test files)
13. requirements.txt
14. README.md
```

---

## ✅ FINAL CHECKLIST (verify before submitting)

- [ ] `uvicorn main:app --reload` starts without errors
- [ ] `/` route serves the React frontend
- [ ] Google OAuth login redirects correctly and returns to app
- [ ] "Analyze My Day" button triggers all 4 APIs and returns Gemini response
- [ ] Priority queue renders with color-coded urgency badges
- [ ] "Copy Reply" copies the drafted email to clipboard
- [ ] Deadline alert section shows or hides based on data
- [ ] `pytest tests/` → all tests pass
- [ ] `.env` is NOT committed (`.gitignore` works)
- [ ] Repo is public, single branch, under 1MB
- [ ] README has all 5 sections

---

*Built for Google Antigravity Prompt Wars — Vertical: Business/Freelance Ops*
