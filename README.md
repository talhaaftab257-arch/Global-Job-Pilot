# Global AI JobPilot — Worldwide AI Jobs & Visa Sponsorship Intelligence Platform

**Global AI JobPilot** is an end-to-end intelligence platform engineered for AI and Machine Learning professionals applying internationally from Pakistan. It continuously discovers worldwide job opportunities from official public employer applicant tracking systems (Greenhouse, Lever, Ashby), identifies genuine visa sponsorship and relocation support, computes intelligent candidate compatibility match scores, prevents duplicate postings, and delivers structured daily reports.

---

## Key Features

- **Pixel-Perfect SaaS Dashboard:** 9 responsive application screens (Dashboard, All Jobs, Job Details, Sponsorship Tracker, Countries, Applications, Sources, Preferences, Settings) styled with deep navy, teal, and emerald accents.
- **Official Public ATS Collectors:** Zero unauthorized web scraping. Direct, compliant integrations with **Greenhouse**, **Lever**, and **Ashby** APIs.
- **Pre-Configured Premier AI Employers:** Curated boards for Anthropic, OpenAI, Stripe, Perplexity, Cursor, ElevenLabs, Scale AI, Databricks, Cloudflare, Figma, Palantir, Spotify, Synthesia, Linear, Ramp, and Writer.
- **Visa Sponsorship Intelligence Engine:** Strict vacancy-specific evidence extraction classifying jobs into `Confirmed`, `Likely`, `Unverified`, or `Unavailable`.
- **AI Compatibility Match Engine:** 100-point heuristic scoring tailored to the candidate's technical profile (Python, FastAPI, LangGraph, RAG, Multi-Agent systems, PyTorch, Docker, Supabase).
- **Application Pipeline Tracker:** Track stages from Saved, Applied, Interview, Offer, to Rejected with custom notes.
- **Free Automated Infrastructure:** GitHub Actions scheduled daily workflow at 03:00 UTC with manual dispatch support and 30-job report selection.
- **Independent Notification Providers:** Structured alerts via Telegram Bot API and responsive HTML emails via Gmail SMTP.
- **Dual Persistence Architecture:** Supabase PostgreSQL with automated resilient SQLite fallback (`backend/data/jobs.db`).

---

## Project Structure

```
job ai global/
├── backend/
│   ├── app/
│   │   ├── collectors/
│   │   │   └── public_ats.py      # Greenhouse, Lever, Ashby API collectors
│   │   ├── services/
│   │   │   ├── matching.py        # 100-point candidate scoring engine
│   │   │   └── sponsorship.py     # Visa & relocation evidence classifier
│   │   ├── config.py              # Pydantic environment configuration
│   │   ├── daily.py               # Daily cron execution & ranking script
│   │   ├── database.py            # Supabase PostgreSQL + SQLite persistence
│   │   ├── main.py                # FastAPI REST API endpoints
│   │   └── notifications.py       # Telegram and HTML email formatters
│   ├── tests/
│   │   ├── test_api.py            # FastAPI integration tests
│   │   └── test_services.py       # Scoring & collector unit tests
│   └── requirements.txt           # Python dependencies
├── src/
│   ├── lib/
│   │   └── supabase.ts            # Supabase client initialization
│   ├── App.tsx                    # 9-screen React application
│   ├── main.tsx                   # React root entrypoint
│   ├── styles.css                 # Custom design system CSS
│   ├── types.ts                   # TypeScript data models
│   └── vite-env.d.ts              # Vite environment typings
├── supabase/
│   └── migrations/
│       └── 202611080001_initial_schema.sql # Database DDL, indexes, and RLS
├── .github/
│   └── workflows/
│       └── daily_jobs.yml         # GitHub Actions scheduled workflow
├── .env.example                   # Environment configuration template
├── IMPLEMENTATION_STATUS.md       # Implementation and verification checklist
├── package.json                   # Frontend dependencies and scripts
└── vite.config.ts                 # Vite bundler configuration
```

---

## Quick Start (Local Setup)

### 1. Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
The application comes pre-configured with active employer boards in `.env`.

### 2. Backend Setup & Run

In a terminal, navigate to the repository:
```powershell
# Set PYTHONPATH and run the FastAPI server
$env:PYTHONPATH="backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Health Check: `http://localhost:8000/api/health`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

### 3. Frontend Setup & Run

In a second terminal:
```powershell
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

### 4. Run Automated Test Suite

```powershell
$env:PYTHONPATH="backend"
python -m pytest -p no:cacheprovider backend/tests
```
All 12 backend unit and API integration tests pass with mocked and live validations.

### 5. Frontend Production Build

```powershell
npm run build
```
Builds the optimized production bundle with zero TypeScript compilation errors.

---

## Database Migration (Supabase)

To enable remote Supabase storage:
1. Open your [Supabase Dashboard](https://supabase.com/dashboard).
2. Go to **SQL Editor** -> **New Query**.
3. Copy and paste the contents of `supabase/migrations/202611080001_initial_schema.sql` and click **Run**.
4. The backend will automatically write to and sync with Supabase tables. (If remote tables are not yet created, the application seamlessly uses local storage without interruptions).

---

## Automated Daily Job Collection

### Manual Trigger:
- Click **"Run Collection Now"** directly on the dashboard sidebar or **"Sync All Sources"** in the Sources screen.
- Or run via CLI:
  ```powershell
  $env:PYTHONPATH="backend"
  python -m app.daily
  ```

### GitHub Actions (03:00 UTC Daily):
Add the following secrets in **GitHub Repository > Settings > Secrets and variables > Actions**:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `EMPLOYER_BOARDS` (or repository variable)
- `TELEGRAM_BOT_TOKEN` (optional)
- `TELEGRAM_CHAT_ID` (optional)
- `SMTP_EMAIL` (optional)
- `SMTP_PASSWORD` (optional)

---

## Security & Privacy

- **Row Level Security (RLS):** All database tables have RLS policies enabled.
- **Backend-Only Service Role:** `SUPABASE_SERVICE_ROLE_KEY` is strictly reserved for the Python backend and GitHub Actions. Never exposed to the frontend.
- **Zero Scraping:** Exclusively uses permitted vendor public APIs with compliant user-agent headers and retry timeouts.
