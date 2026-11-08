"""
Resilient Persistence Layer
Supports Supabase PostgreSQL (primary) with local SQLite fallback.
Handles job deduplication, application tracking, preferences, and execution logs.
"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.config import settings

log = logging.getLogger("jobpilot.database")

DB_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DB_DIR / "jobs.db"

def init_sqlite():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS job_sources (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            board_identifier TEXT NOT NULL,
            source_url TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            last_collected_at TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(source_type, board_identifier)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            source_id TEXT,
            source_name TEXT,
            external_id TEXT NOT NULL,
            canonical_url TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            country TEXT,
            salary_text TEXT,
            description TEXT,
            application_url TEXT NOT NULL,
            posted_at TEXT,
            required_skills TEXT NOT NULL DEFAULT '[]',
            sponsorship_status TEXT NOT NULL DEFAULT 'unverified',
            sponsorship_evidence TEXT,
            sponsorship_source_url TEXT,
            employer_sponsor_verified INTEGER NOT NULL DEFAULT 0,
            relocation_support INTEGER,
            relocation_evidence TEXT,
            work_authorization_requirement TEXT,
            candidate_eligibility TEXT,
            verification_timestamp TEXT,
            match_score INTEGER,
            technical_score INTEGER,
            role_score INTEGER,
            ai_relevance_score INTEGER,
            experience_score INTEGER,
            sponsorship_score INTEGER,
            location_score INTEGER,
            recency_score INTEGER,
            match_explanation TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            remote_type TEXT,
            raw_source_data TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(source_name, external_id)
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS job_runs (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            sources_processed INTEGER NOT NULL DEFAULT 0,
            jobs_discovered INTEGER NOT NULL DEFAULT 0,
            jobs_matched INTEGER NOT NULL DEFAULT 0,
            jobs_saved INTEGER NOT NULL DEFAULT 0,
            duration_seconds REAL,
            errors TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS job_preferences (
            id TEXT PRIMARY KEY,
            target_titles TEXT NOT NULL DEFAULT '[]',
            target_countries TEXT NOT NULL DEFAULT '[]',
            target_regions TEXT NOT NULL DEFAULT '[]',
            skills TEXT NOT NULL DEFAULT '[]',
            minimum_match_score INTEGER NOT NULL DEFAULT 70,
            sponsorship_priority INTEGER NOT NULL DEFAULT 1,
            relocation_preference INTEGER NOT NULL DEFAULT 1,
            remote_preference INTEGER NOT NULL DEFAULT 1,
            telegram_enabled INTEGER NOT NULL DEFAULT 0,
            email_enabled INTEGER NOT NULL DEFAULT 0,
            daily_notification_limit INTEGER NOT NULL DEFAULT 30,
            updated_at TEXT NOT NULL
        );
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'saved',
            applied_at TEXT,
            interview_at TEXT,
            follow_up_at TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        conn.commit()

init_sqlite()

def get_db_client():
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    try:
        from supabase import create_client
        return create_client(settings.supabase_url, settings.supabase_service_role_key)
    except Exception as exc:
        log.warning(f"Could not initialize Supabase client: {exc}")
        return None

def save_job_supabase(client, source_type: str, board: str, job: dict) -> bool:
    roots = {
        "greenhouse": "https://boards.greenhouse.io/",
        "lever": "https://jobs.lever.co/",
        "ashby": "https://jobs.ashbyhq.com/"
    }
    source = client.table("job_sources").upsert({
        "source_type": source_type,
        "board_identifier": board,
        "name": f"{source_type.title()} · {board}",
        "source_url": roots.get(source_type, "") + board,
        "active": True
    }, on_conflict="source_type,board_identifier").execute()

    if source.data:
        job["source_id"] = source.data[0]["id"]

    # Match by canonical URL first, then source_name + external_id
    existing = client.table("jobs").select("id").eq("canonical_url", job["canonical_url"]).limit(1).execute().data
    if not existing:
        existing = client.table("jobs").select("id").eq("source_name", job.get("source_name")).eq("external_id", job["external_id"]).limit(1).execute().data

    # Supabase expects json arrays for text[]
    sb_job = dict(job)
    if "remote_type" in sb_job:
        sb_job.pop("remote_type", None)

    if existing:
        client.table("jobs").update(sb_job).eq("id", existing[0]["id"]).execute()
        return False

    client.table("jobs").insert(sb_job).execute()
    return True

def save_job_sqlite(source_type: str, board: str, job: dict) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    roots = {
        "greenhouse": "https://boards.greenhouse.io/",
        "lever": "https://jobs.lever.co/",
        "ashby": "https://jobs.ashbyhq.com/"
    }
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Upsert source
        cur.execute("SELECT id FROM job_sources WHERE source_type=? AND board_identifier=?", (source_type, board))
        s_row = cur.fetchone()
        if not s_row:
            s_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO job_sources (id, name, source_type, board_identifier, source_url, active, last_collected_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                (s_id, f"{source_type.title()} · {board}", source_type, board, roots.get(source_type, "") + board, now, now)
            )
        else:
            s_id = s_row["id"]
            cur.execute("UPDATE job_sources SET last_collected_at=? WHERE id=?", (now, s_id))

        # Check existing job
        cur.execute("SELECT id FROM jobs WHERE canonical_url=?", (job["canonical_url"],))
        j_row = cur.fetchone()
        if not j_row:
            cur.execute("SELECT id FROM jobs WHERE source_name=? AND external_id=?", (job.get("source_name"), job["external_id"]))
            j_row = cur.fetchone()

        skills_json = json.dumps(job.get("required_skills", []))
        raw_json = json.dumps(job.get("raw_source_data", {}))

        if j_row:
            # Update existing
            job_id = j_row["id"]
            cur.execute("""
            UPDATE jobs SET
                title=?, company=?, location=?, country=?, salary_text=?, description=?,
                application_url=?, posted_at=?, required_skills=?, sponsorship_status=?,
                sponsorship_evidence=?, relocation_support=?, relocation_evidence=?,
                work_authorization_requirement=?, candidate_eligibility=?, match_score=?,
                technical_score=?, role_score=?, ai_relevance_score=?, experience_score=?,
                sponsorship_score=?, location_score=?, recency_score=?, match_explanation=?,
                remote_type=?, updated_at=?
            WHERE id=?
            """, (
                job["title"], job["company"], job.get("location"), job.get("country"),
                job.get("salary_text"), job.get("description"), job["application_url"],
                job.get("posted_at"), skills_json, job.get("sponsorship_status", "unverified"),
                job.get("sponsorship_evidence"), 1 if job.get("relocation_support") else 0,
                job.get("relocation_evidence"), job.get("work_authorization_requirement"),
                job.get("candidate_eligibility"), job.get("match_score"),
                job.get("technical_score"), job.get("role_score"), job.get("ai_relevance_score"),
                job.get("experience_score"), job.get("sponsorship_score"), job.get("location_score"),
                job.get("recency_score"), job.get("match_explanation"), job.get("remote_type"),
                now, job_id
            ))
            conn.commit()
            return False
        else:
            job_id = str(uuid.uuid4())
            cur.execute("""
            INSERT INTO jobs (
                id, source_id, source_name, external_id, canonical_url, title, company,
                location, country, salary_text, description, application_url, posted_at,
                required_skills, sponsorship_status, sponsorship_evidence, relocation_support,
                relocation_evidence, work_authorization_requirement, candidate_eligibility,
                verification_timestamp, match_score, technical_score, role_score,
                ai_relevance_score, experience_score, sponsorship_score, location_score,
                recency_score, match_explanation, status, remote_type, raw_source_data,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, 'open', ?, ?,
                ?, ?
            )
            """, (
                job_id, s_id, job.get("source_name"), job["external_id"], job["canonical_url"],
                job["title"], job["company"], job.get("location"), job.get("country"),
                job.get("salary_text"), job.get("description"), job["application_url"],
                job.get("posted_at"), skills_json, job.get("sponsorship_status", "unverified"),
                job.get("sponsorship_evidence"), 1 if job.get("relocation_support") else 0,
                job.get("relocation_evidence"), job.get("work_authorization_requirement"),
                job.get("candidate_eligibility"), job.get("verification_timestamp"),
                job.get("match_score"), job.get("technical_score"), job.get("role_score"),
                job.get("ai_relevance_score"), job.get("experience_score"),
                job.get("sponsorship_score"), job.get("location_score"),
                job.get("recency_score"), job.get("match_explanation"),
                job.get("remote_type"), raw_json, now, now
            ))
            conn.commit()
            return True

def save_job(db, source_type: str, board: str, job: dict) -> bool:
    """Save to Supabase if accessible, and always mirror into local SQLite storage."""
    is_new = False
    if db:
        try:
            is_new = save_job_supabase(db, source_type, board, job)
        except Exception as exc:
            log.warning(f"Supabase save failed ({exc}); persisting locally to SQLite")
            is_new = save_job_sqlite(source_type, board, job)
    else:
        is_new = save_job_sqlite(source_type, board, job)
    return is_new

def list_jobs_sqlite(limit=100, offset=0, sponsorship=None, country=None, query=None, min_score=None, sort="match") -> dict:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        conditions = ["status = 'open'"]
        params = []
        if sponsorship and sponsorship != "all":
            conditions.append("sponsorship_status = ?")
            params.append(sponsorship)
        if country and country != "all":
            conditions.append("country = ?")
            params.append(country)
        if min_score:
            conditions.append("match_score >= ?")
            params.append(int(min_score))
        if query:
            conditions.append("(title LIKE ? OR company LIKE ? OR location LIKE ? OR description LIKE ? OR external_id LIKE ?)")
            q_like = f"%{query}%"
            params.extend([q_like, q_like, q_like, q_like, q_like])

        where_clause = " WHERE " + " AND ".join(conditions)

        # Count total
        cur.execute(f"SELECT COUNT(*) FROM jobs{where_clause}", params)
        total = cur.fetchone()[0]

        order_by = "match_score DESC, posted_at DESC" if sort == "match" else "posted_at DESC, match_score DESC"
        cur.execute(f"SELECT * FROM jobs{where_clause} ORDER BY {order_by} LIMIT ? OFFSET ?", params + [limit, offset])

        items = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["required_skills"] = json.loads(d.get("required_skills") or "[]")
            except Exception:
                d["required_skills"] = []
            d["relocation_support"] = bool(d.get("relocation_support"))
            items.append(d)

        return {"items": items, "total": total, "configured": True}

def get_job_sqlite(job_id: str) -> dict | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["required_skills"] = json.loads(d.get("required_skills") or "[]")
        except Exception:
            d["required_skills"] = []
        d["relocation_support"] = bool(d.get("relocation_support"))
        return d

def record_job_run_sqlite(sources: int, discovered: int, saved: int, duration: float, errors: list, status="completed"):
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO job_runs (id, started_at, finished_at, status, sources_processed, jobs_discovered, jobs_matched, jobs_saved, duration_seconds, errors, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), now, now, status, sources, discovered, saved, saved, duration, json.dumps(errors), now)
        )
        conn.commit()
