# OpsCore — Smart Freelance Ops Assistant

## Chosen Vertical
Business / Freelance Operations

## Problem Statement
Solo freelancers and developers juggle dozens of async client conversations across Gmail, Calendar deadlines, and shared Drive documents — often across multiple timezones. Without a unified view, critical tasks fall through the cracks, replies get delayed, and deadlines are missed. OpsCore solves this by aggregating all three data sources into a single AI-powered priority queue that tells you exactly what to work on next and drafts the most urgent reply for you.

## Approach and Logic
OpsCore connects four Google services through a single orchestration layer:

1. **Gmail API** — Fetches the last 10 inbox emails (metadata + snippet) to understand what clients are asking for.
2. **Google Calendar API** — Pulls today's events to identify meetings, calls, and time-blocked commitments.
3. **Google Drive API** — Retrieves the 5 most recently modified files to surface active documents and deliverables.
4. **Gemini 1.5 Flash API** — All three data sources are bundled into a single structured prompt. Gemini analyzes the context and returns a JSON response containing:
   - A **Priority Queue** (top 3 tasks ranked by urgency)
   - A **Drafted Reply** for the most urgent email
   - A **Deadline Alert** if anything is due within 24 hours

The architecture enforces strict separation of concerns — each service file handles only its own API. All orchestration happens in a single route handler that collects data, builds one prompt, and makes one Gemini call. OAuth tokens are stored in encrypted sessions (never written to disk), and all user data is ephemeral — fetched fresh on every analysis and discarded after the response.

## How to Run
1. Clone the repo
   ```bash
   git clone https://github.com/yourusername/opscore.git
   cd opscore
   ```
2. Copy `.env.example` to `.env` and fill in your Google Cloud credentials and Gemini API key
   ```bash
   cp .env.example .env
   ```
3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
4. Start the server
   ```bash
   uvicorn opscore.main:app --reload
   ```
5. Open [http://localhost:8000](http://localhost:8000) in your browser

### Google Cloud Setup
- Create a project in [Google Cloud Console](https://console.cloud.google.com)
- Enable Gmail API, Google Calendar API, and Google Drive API
- Create OAuth 2.0 credentials (Web application type)
- Add `http://localhost:8000/auth/callback` as an authorized redirect URI
- Get a Gemini API key from [Google AI Studio](https://aistudio.google.com)

## Assumptions
- The user has a Google account with Gmail, Calendar, and Drive enabled.
- The Google Cloud project has the required APIs enabled and OAuth consent screen configured.
- The application runs locally on `http://localhost:8000` (no production deployment assumed).
- The user's primary calendar is the one being queried for events.
- All email analysis is based on metadata and snippets — full email body content is not fetched for privacy.
- The Gemini API key has sufficient quota for the `gemini-1.5-flash` model.
- The application is single-user — no multi-tenant session management is implemented.
