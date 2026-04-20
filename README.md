# OpsCore — AI-Powered Freelance Operations Platform

OpsCore is a production-grade, multi-agent AI system built for **Hack2Skill PromptWars 2026**. It unifies Gmail, Google Calendar, Google Drive, and Google Sheets into a single intelligent command center — eliminating the tab-switching chaos that costs freelancers 20–30% of their productivity.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| **On-Demand AI Analytics** | Full-page analytics engine with priority ranking (High/Medium/Low) and AI-generated reports |
| **Multi-Provider BYOK** | Add API keys for Gemini, OpenAI, Anthropic, Grok, Mistral, DeepSeek — with failover support |
| **Token-Aware Architecture** | User-configurable analysis scope (1–50 items) with cost warnings before every AI call |
| **Native Email Rendering** | Sandboxed iframe with smart HTML/plain-text detection for proper email display |
| **One-Click Actions** | Deep Summarize, Draft Reply, Graphify Data, Inject to Calendar — all AI-powered |
| **Secure Key Storage** | API keys encrypted in HttpOnly cookies via `itsdangerous` — never in localStorage |
| **Auto-Dismissing Errors** | 15-second countdown error bar with manual dismiss |

---

## 🧠 AI Architecture

OpsCore uses a **4-agent orchestration pipeline** coordinated by `asyncio.gather`:

| Agent | Responsibility |
|---|---|
| `EmailAgent` | Classifies threads by urgency, generates context-aware drafts |
| `CalendarAgent` | Extracts deadlines, detects conflicts, suggests focus blocks |
| `ReportAgent` | Synthesizes Drive files and Sheets into project status reports |
| `OpsOrchestrator` | Coordinates all agents concurrently, merges outputs |

**Supported Models (BYOK via LiteLLM):**
- Gemini 2.5 Preview / 2.0 Flash (native Google GenAI SDK)
- OpenAI GPT-4o / GPT-4o Mini
- Anthropic Claude 3.5 Sonnet
- xAI Grok
- Mistral, Cohere, DeepSeek

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────┐
│              Next.js 14 Frontend                │
│   Dashboard │ Analytics │ Settings │ Actions    │
└──────────────────┬──────────────────────────────┘
                   │ HTTP + Cookies (HttpOnly)
┌──────────────────▼──────────────────────────────┐
│              FastAPI Backend                    │
│  ┌─────────────────────────────────────────┐   │
│  │           OpsOrchestrator               │   │
│  │  EmailAgent │ CalendarAgent │ ReportAgent│   │
│  └──────┬──────────────┬───────────────────┘   │
│         │              │                        │
│  Google APIs      LiteLLM Router               │
│  Gmail │ Calendar  Gemini │ GPT-4o │ Claude    │
│  Drive │ Sheets    Grok │ Mistral │ DeepSeek   │
│         │                                      │
│    SQLite DB (Historical Analysis Cache)       │
└─────────────────────────────────────────────────┘
```

Data flow:
1. **Login** → Google OAuth2 → raw data fetched via `asyncio.gather` (no AI call)
2. **Browse** → Emails, Calendar, Drive displayed instantly
3. **Analyze** → User opens Analytics → confirms token warning → single AI call returns priority queue + report
4. **Act** → Click priority items to jump to source → Draft Reply, Summarize, Graphify

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TailwindCSS, Framer Motion, Recharts, ReactMarkdown |
| Backend | FastAPI (Python 3.10+), Uvicorn |
| AI | Google GenAI SDK, LiteLLM (multi-provider router) |
| Auth | Google OAuth2 (OpenID Connect) |
| Security | HttpOnly encrypted cookies (`itsdangerous`) |
| Database | SQLite via SQLAlchemy |
| Deploy | Docker, Google Cloud Run, Supervisor |

---

## ⚙️ Local Development

### Prerequisites
- Python 3.10+
- Node.js 18+
- GCP project with Gmail, Calendar, Drive, and Sheets APIs enabled
- OAuth2 credentials (Web Application type)

### 1. Clone & Configure

```bash
git clone https://github.com/RajTewari01/opscore-freelance-assistant.git
cd opscore-freelance-assistant
cp .env.example .env
# Fill in: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, APP_SECRET_KEY
```

### 2. Backend

```bash
pip install -r opscore/requirements.txt
python main.py                    # → http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                       # → http://localhost:3000
```

Open **http://localhost:3000**, sign in with Google, add your AI key in Settings, and start working.

---

## 🚀 Cloud Deployment (Google Cloud Run)

### 1. Build & Push Docker Image

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/opscore
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy opscore \
  --image gcr.io/YOUR_PROJECT_ID/opscore \
  --platform managed \
  --region us-central1 \
  --port 3000 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLIENT_ID=xxx,GOOGLE_CLIENT_SECRET=xxx,APP_SECRET_KEY=xxx,BACKEND_URL=http://localhost:8000,OAUTHLIB_RELAX_TOKEN_SCOPE=1"
```

### 3. Update OAuth Redirect

In [GCP Console → Credentials](https://console.cloud.google.com/apis/credentials):
- Add your Cloud Run URL to **Authorized redirect URIs**: `https://your-app-xxx.run.app/auth/callback`
- Add to **Authorized JavaScript origins**: `https://your-app-xxx.run.app`

### Alternative: Railway / Render

```bash
# Railway (one-click)
railway login
railway init
railway up

# Render — connect GitHub repo, set environment variables in dashboard
```

---

## 🔐 Google API Scopes

| Scope | Purpose |
|---|---|
| `gmail.readonly` + `gmail.send` | Read inbox + send drafted replies |
| `calendar.events` | Read events + create new events |
| `drive.metadata.readonly` | List recently modified project files |
| `spreadsheets.readonly` | Read sheets for report generation |

---

## 📝 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/auth/login` | Initiates Google OAuth2 flow |
| `GET` | `/auth/status` | Returns auth status + user profile |
| `POST` | `/api/fetch-data` | Fetches raw data from all Google APIs (no AI) |
| `POST` | `/api/analytics` | Runs AI priority analysis + generates report |
| `POST` | `/api/analyze` | Full orchestrator pipeline (legacy) |
| `POST` | `/api/action` | Execute actions (summarize, draft, graphify, calendar) |
| `GET` | `/api/history` | Retrieve past analysis runs from SQLite |

---

## 📂 Project Structure

```
opscore-freelance-assistant/
├── frontend/              # Next.js 14 UI
│   ├── app/page.tsx       # Main dashboard (single-page app)
│   └── next.config.ts     # Proxy config + standalone output
├── opscore/               # FastAPI backend
│   ├── main.py            # App factory + CORS + middleware
│   ├── routes/
│   │   ├── auth.py        # OAuth2 + key encryption
│   │   └── assistant.py   # All API endpoints
│   ├── agents/
│   │   └── orchestrator.py # Multi-agent coordinator
│   ├── services/
│   │   ├── gmail_service.py
│   │   ├── calendar_service.py
│   │   ├── gemini_service.py
│   │   └── sheets_service.py
│   └── models/
│       ├── schemas.py     # Pydantic request/response models
│       └── db_models.py   # SQLAlchemy ORM
├── Dockerfile             # Multi-stage production build
├── supervisord.conf       # Process manager for Docker
├── main.py                # Backend entry point
└── .env.example           # Environment template
```

---

*Built for PromptWars 2026 × Hack2Skill × Google Cloud*
