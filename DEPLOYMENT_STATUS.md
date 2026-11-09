# Deployment Status

Last reviewed: 2026-11-09

## Audit and local implementation

- Confirmed the project contains a Vite/React frontend, FastAPI API, Supabase schema, and a GitHub Actions daily collection workflow.
- Replaced the active Telegram sender with Discord webhook reports, high-priority alerts, collection summaries, and failure reports. Gmail SMTP remains an independent sender.
- Added webhook-safe logging, bounded retries for transient Discord failures, compact embeds, and duplicate removal within each report.
- Added a Supabase migration that keeps notification history, moves old provider history to a neutral legacy label, migrates the notification preference, and removes the retired preference column.
- Added Supabase Auth sign-in/sign-up in the UI and bearer-token validation for API routes. Applications and preferences are scoped to the authenticated user.
- Replaced the legacy-only Supabase SDK path with a REST/Auth client that accepts the current secret-key format and legacy service-role JWT keys.
- Added Vercel SPA configuration and a backend deployment ignore file. The frontend and FastAPI backend are intended to be separate Vercel projects from one Git repository.
- Updated `.env.example`, GitHub Actions secrets, README instructions, and prior project notes for Discord and Supabase Auth.
- `.env` remains ignored by Git; no credential values were copied into source or deployment documentation.

## Verification

- Backend API health: `ok`; Supabase reachable; 3,895 open jobs returned from the existing project.
- Unauthenticated API request: rejected with HTTP 401.
- Backend tests: **12 passed** using a temporary SQLite database with live Supabase writes disabled.
- Frontend production build: **passed**. Vite reports a 879 kB JavaScript chunk warning; it does not block the build.
- Discord delivery: not tested because no webhook URL is configured.
- Gmail delivery: not tested because SMTP credentials are not configured.
- Supabase migration `202611080002_discord_notifications.sql`: prepared but not applied to the live database.

## Deployment status

No public deployment has been made. `git remote -v` returned no remote, so Vercel cannot be connected to the source repository and GitHub Actions cannot receive the updated workflow. No live Vercel URL or workflow run is available to report.

The backend can run locally and reaches the configured Supabase project. The checked-in workflow is ready to run after the repository is connected and its secrets/variables are added.

## Remaining setup

1. Connect this repository to GitHub and configure the origin remote.
2. Apply `supabase/migrations/202611080002_discord_notifications.sql` in the existing Supabase project. Keep the initial migration unchanged on an already-populated project.
3. Confirm Supabase email sign-up is enabled and add the deployed frontend URL to Auth redirect URLs.
4. Create the Vercel frontend project at the repository root and the backend project with root directory `backend`. Set the environment variables described in README.
5. Create a Discord channel webhook and add `DISCORD_WEBHOOK_URL` to the backend and GitHub Actions secrets.
6. Add Gmail SMTP credentials as backend/GitHub secrets if email reports are wanted.
7. Add GitHub secrets `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (or the legacy `SUPABASE_SERVICE_ROLE_KEY`), `DISCORD_WEBHOOK_URL`, `SMTP_EMAIL`, and `SMTP_PASSWORD`. Add `EMPLOYER_BOARDS`, `SMTP_HOST`, and `SMTP_PORT` as repository variables.
8. Configure the frontend's `VITE_API_BASE_URL` with the backend Vercel origin and the backend's `FRONTEND_URL` with the frontend origin.

No user-facing webhook or email was sent during this work.
