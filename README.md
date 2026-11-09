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
- **Independent Notification Providers:** Structured alerts via Discord webhooks and responsive HTML emails via Gmail SMTP.
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
│   │   └── notifications/         # Discord webhook and HTML email delivery
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
The API integration tests use the local SQLite fallback. Do not configure real notification secrets for test runs.

### 5. Frontend Production Build

```powershell
npm run build
```
Builds the optimized production bundle with zero TypeScript compilation errors.

---

## Supabase Setup

1. Set `SUPABASE_URL` and `SUPABASE_SECRET_KEY` in the backend environment. Legacy `SUPABASE_SERVICE_ROLE_KEY` is also accepted. Keep the elevated key server-side.
2. Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in the frontend environment. The anon key is public and relies on RLS.
3. Apply both files in `supabase/migrations/` in filename order. For an existing database created from migration `202611080001`, apply only `202611080002_discord_notifications.sql`.
4. Enable email sign-up in Supabase Authentication and add the deployed frontend URL to the allowed redirect URLs.

The FastAPI API verifies each Supabase access token. Application and preference rows are scoped to that authenticated user. Supabase service credentials never go to the browser.

---

## Automated Daily Job Collection

### Local Manual Trigger:
- Click **"Run Collection Now"** from the dashboard while using the local development server.
- Or run via CLI:
  ```powershell
  $env:PYTHONPATH="backend"
  python -m app.daily
  ```

### GitHub Actions (03:00 UTC daily):
The workflow also supports manual dispatch in GitHub Actions. Add these secrets in **Repository > Settings > Secrets and variables > Actions**:
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (or legacy `SUPABASE_SERVICE_ROLE_KEY`)
- `DISCORD_WEBHOOK_URL`
- `SMTP_EMAIL`
- `SMTP_PASSWORD`

Add `EMPLOYER_BOARDS`, `SMTP_HOST`, `SMTP_PORT`, and `GROQ_MODEL` as repository variables. `GROQ_API_KEY` is optional. Scheduled workflow timing can be delayed by GitHub.

---

## Security & Privacy

- **Row Level Security (RLS):** All database tables have RLS policies enabled.
- **Backend-Only Secret:** `SUPABASE_SECRET_KEY` (or the legacy service role key) is restricted to the Python backend and GitHub Actions. It is never exposed to the frontend.
- **Zero Scraping:** Exclusively uses permitted vendor public APIs with compliant user-agent headers and retry timeouts.

## Production Deployment

Deploy two Vercel projects from the same Git repository:

1. **Frontend:** project root is the repository root. Use the Vite preset, `npm run build`, and output directory `dist`. `vercel.json` provides SPA route fallback.
2. **Backend:** project root is `backend`. Vercel detects the FastAPI app in `app/main.py`; Python dependencies are listed in `backend/requirements.txt`.

Set frontend environment variables in Vercel:

- `VITE_API_BASE_URL`: the backend project's HTTPS origin, with no trailing slash.
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Set backend environment variables in Vercel:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` (or legacy `SUPABASE_SERVICE_ROLE_KEY`)
- `FRONTEND_URL`: the deployed frontend origin, for CORS.
- `EMPLOYER_BOARDS`
- `DISCORD_WEBHOOK_URL`
- `SMTP_EMAIL`, `SMTP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT`
- `LOCAL_AUTH_BYPASS=false`
- Optional `GROQ_API_KEY` and `GROQ_MODEL`

Set up Discord from **Server Settings → Integrations → Webhooks → New Webhook**, select the daily-alert channel, and save the webhook URL as a secret. For Gmail, use an app password with 2-Step Verification enabled. Never put either credential in a `VITE_` variable.

The deployed backend uses Supabase for shared jobs, applications, preferences, and analytics. Its SQLite file is only a temporary local fallback in serverless deployments. Collection runs from the GitHub Actions workflow; the local-only API trigger is not exposed publicly.
