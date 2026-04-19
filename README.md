# OpsCore: Pro-Grade AI Freelance Assistant

OpsCore is a powerful, multi-model Freelance Assistant built for the **Hack2Skill PromptWars** competition. It solves the "Data Fragmentation" problem for independent developers by unifying Gmail, Google Calendar, Google Drive, and Google Sheets into a single, intelligent "Command Center."

---

## 🚀 The Vertical: Freelance Operations Assistant
Freelancers often lose 20-30% of their productivity switching between email, calendars, and project spreadsheets. OpsCore serves as a virtual ops manager that aggregates this data, provides intelligent prioritization, and drafts replies automatically—allowing the freelancer to focus entirely on code.

## 🧠 Approach & AI Architecture
OpsCore uses a **Hybrid BYOK (Bring Your Own Key)** architecture:
- **Native Google GenAI (v1 SDK)**: We utilize the latest Google GenAI Python SDK for seamless, native integration with **Gemini 2.0 Flash** and **Gemini 2.5 Preview** models. This ensures the best performance and lowest latency for Google-centric workflows.
- **Provider Agnostic (LiteLLM)**: We integrate **LiteLLM** as a universal router, allowing users to plug in keys for **OpenAI (GPT-4o)**, **Anthropic (Claude 3.5)**, and **xAI (Grok)**.
- **Stateless Backend**: The architecture is entirely stateless. API keys are stored securely in the user's browser `localStorage` and injected via secure headers (`x-ai-provider`, `x-ai-key`) for each request.

## 🛠️ How It Works (Logic)
1. **Multi-Source Context Harvesting**: On "Fetch Global," the backend concurrently pulls:
   - Recent high-priority emails.
   - Upcoming schedule and deadline events.
   - Recently modified project files and shared spreadsheets.
2. **Contextual Analysis**: The harvested data is stitched into a Master Context Prompt.
3. **GenAI Prioritization**: The AI (Gemini/Claude/GPT) analyzes the context to:
   - Rank and rationalize top tasks.
   - Detect looming deadlines.
   - Draft context-aware email replies for the most urgent threads.
4. **Dynamic UI**: Built with **Next.js** and **Framer Motion**, providing a premium, "OS-like" experience with real-time data visualization via **Recharts**.

## 📝 Assumptions
- **API Access**: Assumes the user has active Google Cloud credentials and has authorized the relevant scopes (Gmail, Calendar, Drive, Sheets).
- **BYOK**: Assumes the user provides valid API keys for their chosen models.
- **Connectivity**: Requires an active internet connection to reach Google Services and LLM providers.

## 🛠️ Technical Stack
- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: Next.js 14, TailwindCSS (for base), Framer Motion
- **AI**: Google GenAI, LiteLLM
- **Auth**: Google OAuth2 (OpenID Connect)

---

### 📋 Setup & Installation
1. Clone the repository.
2. Install Python dependencies: `uv pip install -r pyproject.toml`
3. Set up your `.env` with `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GEMINI_API_KEY`.
4. Run the backend: `python main.py`
5. Navigate to the dashboard, select your model in **Settings**, enter your key, and start fetching!

---

*Developed for PromptWars 2026.*
