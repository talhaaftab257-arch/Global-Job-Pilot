create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(), user_id uuid unique references auth.users(id) on delete cascade,
  full_name text, location text default 'Rawalpindi, Pakistan', nationality text default 'Pakistani',
  current_title text default 'AI Engineer', skills text[] not null default '{}', portfolio_url text,
  preferences jsonb not null default '{}', created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists public.job_sources (
  id uuid primary key default gen_random_uuid(), name text not null, source_type text not null check(source_type in ('greenhouse','lever','ashby','feed','employer')),
  board_identifier text not null, source_url text, active boolean not null default true, last_collected_at timestamptz,
  created_at timestamptz not null default now(), unique(source_type,board_identifier)
);
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(), source_id uuid references public.job_sources(id) on delete set null,
  source_name text, external_id text not null, canonical_url text not null unique, title text not null, company text not null,
  location text, country text, salary_text text, description text, application_url text not null, posted_at timestamptz,
  required_skills text[] not null default '{}', sponsorship_status text not null default 'unverified' check(sponsorship_status in ('confirmed','likely','unverified','unavailable')),
  sponsorship_evidence text, sponsorship_source_url text, employer_sponsor_verified boolean not null default false,
  relocation_support boolean, relocation_evidence text, work_authorization_requirement text, candidate_eligibility text,
  verification_timestamp timestamptz, match_score integer check(match_score between 0 and 100), technical_score integer,
  role_score integer, ai_relevance_score integer, experience_score integer, sponsorship_score integer, location_score integer,
  recency_score integer, match_explanation text, status text not null default 'open' check(status in ('open','closed','expired')),
  raw_source_data jsonb not null default '{}', created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(source_name,external_id)
);
create table if not exists public.job_runs (
  id uuid primary key default gen_random_uuid(), started_at timestamptz not null default now(), finished_at timestamptz,
  status text not null default 'running', sources_processed integer not null default 0, jobs_discovered integer not null default 0,
  jobs_matched integer not null default 0, jobs_saved integer not null default 0, duration_seconds numeric,
  errors jsonb not null default '[]', created_at timestamptz not null default now()
);
create table if not exists public.job_preferences (
  id uuid primary key default gen_random_uuid(), user_id uuid unique references auth.users(id) on delete cascade,
  target_titles text[] not null default '{}', target_countries text[] not null default '{}', target_regions text[] not null default '{}',
  skills text[] not null default '{}', minimum_match_score integer not null default 70, sponsorship_priority boolean not null default true,
  relocation_preference boolean not null default true, remote_preference boolean not null default true,
  telegram_enabled boolean not null default false, email_enabled boolean not null default false,
  daily_notification_limit integer not null default 30 check(daily_notification_limit between 1 and 30), updated_at timestamptz not null default now()
);
create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete cascade,
  job_id uuid not null references public.jobs(id) on delete cascade, status text not null default 'saved' check(status in ('saved','applied','interview','offer','rejected','follow_up')),
  applied_at timestamptz, interview_at timestamptz, follow_up_at timestamptz, notes text, created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(user_id,job_id)
);
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(), user_id uuid references auth.users(id) on delete cascade,
  channel text not null check(channel in ('telegram','email')), status text not null default 'pending',
  job_run_id uuid references public.job_runs(id) on delete set null, recipient text, job_count integer not null default 0,
  error text, sent_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.employer_sponsorship (
  id uuid primary key default gen_random_uuid(), employer_name text not null, country text, official_source_url text,
  sponsor_status text, verified_at timestamptz, evidence text, created_at timestamptz not null default now(), unique(employer_name,country)
);

create index if not exists jobs_match_score_idx on public.jobs(match_score desc nulls last);
create index if not exists jobs_status_posted_idx on public.jobs(status,posted_at desc);
create index if not exists jobs_sponsorship_country_idx on public.jobs(sponsorship_status,country);
create index if not exists jobs_company_title_idx on public.jobs(company,title);
create index if not exists applications_user_status_idx on public.applications(user_id,status,updated_at desc);
create index if not exists job_runs_started_idx on public.job_runs(started_at desc);

alter table public.profiles enable row level security;
alter table public.job_sources enable row level security;
alter table public.jobs enable row level security;
alter table public.job_runs enable row level security;
alter table public.job_preferences enable row level security;
alter table public.applications enable row level security;
alter table public.notifications enable row level security;
alter table public.employer_sponsorship enable row level security;

create policy "authenticated users read jobs" on public.jobs for select to authenticated using (true);
create policy "authenticated users read sources" on public.job_sources for select to authenticated using (active);
create policy "users manage own profile" on public.profiles for all to authenticated using (auth.uid()=user_id) with check (auth.uid()=user_id);
create policy "users manage own preferences" on public.job_preferences for all to authenticated using (auth.uid()=user_id) with check (auth.uid()=user_id);
create policy "users manage own applications" on public.applications for all to authenticated using (auth.uid()=user_id) with check (auth.uid()=user_id);
create policy "users read own notifications" on public.notifications for select to authenticated using (auth.uid()=user_id);
create policy "authenticated users read sponsor register" on public.employer_sponsorship for select to authenticated using (true);
create policy "authenticated users read job runs" on public.job_runs for select to authenticated using (true);
