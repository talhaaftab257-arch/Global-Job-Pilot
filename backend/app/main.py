import logging
import time
import ipaddress
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.collectors.public_ats import COLLECTORS
from app.database import (
    get_db_client, save_job, list_jobs_sqlite, get_job_sqlite,
    record_job_run_sqlite, DB_PATH
)
from app.notifications import format_email, format_telegram, send_email, send_telegram

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("jobpilot.api")

app = FastAPI(
    title="Global AI JobPilot API",
    description="Worldwide AI jobs & visa sponsorship intelligence platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/api/health")
def health():
    db = get_db_client()
    configured_sources = [
        item.strip() for item in settings.employer_boards.split(",")
        if ":" in item.strip()
    ]
    # Check jobs count from local database
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM jobs WHERE status='open'")
        local_jobs_count = cur.fetchone()[0]

    return {
        "status": "ok",
        "database_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "sources_configured": len(configured_sources),
        "total_jobs": local_jobs_count,
        "ai_engine": "rule-based heuristic active" + (" (OpenAI configured)" if settings.openai_api_key else "")
    }

@app.get("/api/jobs")
def jobs(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sponsorship: str | None = None,
    country: str | None = None,
    query: str | None = None,
    sort: str = "match"
):
    db = get_db_client()
    if db:
        try:
            q = db.table("jobs").select("*").eq("status", "open")
            if sponsorship and sponsorship != "all":
                q = q.eq("sponsorship_status", sponsorship)
            if country and country != "all":
                q = q.eq("country", country)
            if sort == "date":
                q = q.order("posted_at", desc=True)
            else:
                q = q.order("match_score", desc=True)

            res = q.range(offset, offset + limit - 1).execute()
            if res.data is not None and len(res.data) > 0:
                items = res.data
                if query:
                    items = [
                        j for j in items
                        if query.lower() in f"{j.get('title','')} {j.get('company','')} {j.get('location','')} {j.get('description','')}".lower()
                    ]
                return {"items": items, "total": len(items), "configured": True}
        except Exception as exc:
            log.warning(f"Supabase jobs query error ({exc}); using local storage")

    return list_jobs_sqlite(
        limit=limit,
        offset=offset,
        sponsorship=sponsorship,
        country=country,
        query=query,
        sort=sort
    )

@app.get("/api/jobs/featured")
def featured():
    return jobs(limit=30, offset=0, sort="match")

@app.get("/api/jobs/sponsorship")
def sponsorship(status: str | None = None):
    return jobs(limit=250, offset=0, sponsorship=status)

@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    db = get_db_client()
    if db:
        try:
            r = db.table("jobs").select("*").eq("id", job_id).maybe_single().execute()
            if r.data:
                return r.data
        except Exception:
            pass

    job = get_job_sqlite(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@app.get("/api/analytics/overview")
def overview():
    res = list_jobs_sqlite(limit=1000, offset=0)
    items = res["items"]
    counts = {
        s: sum(1 for j in items if j.get("sponsorship_status") == s)
        for s in ["confirmed", "likely", "unverified", "unavailable"]
    }
    avg_match = (
        round(sum(j.get("match_score") or 0 for j in items) / len(items))
        if items else 0
    )
    countries = {j.get("country") for j in items if j.get("country")}

    return {
        "total_jobs": len(items),
        "matching_jobs": sum(1 for j in items if (j.get("match_score") or 0) >= 70),
        "average_match": avg_match,
        "sponsorship": counts,
        "countries": len(countries)
    }

@app.get("/api/analytics/countries")
def countries():
    items = list_jobs_sqlite(limit=1000, offset=0)["items"]
    out = {}
    for j in items:
        c = j.get("country") or "Other"
        v = out.setdefault(c, {"country": c, "jobs": 0, "confirmed": 0, "match_total": 0})
        v["jobs"] += 1
        v["confirmed"] += int(j.get("sponsorship_status") == "confirmed")
        v["match_total"] += j.get("match_score") or 0

    return [
        {
            **v,
            "average_match": round(v["match_total"] / v["jobs"]) if v["jobs"] else 0
        }
        for v in sorted(out.values(), key=lambda x: x["jobs"], reverse=True)
    ]

@app.get("/api/sources")
def get_sources():
    items = []
    # Count jobs per source from local DB
    source_counts = {}
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT source_name, COUNT(*) FROM jobs GROUP BY source_name")
        for s_name, count in cur.fetchall():
            if s_name:
                source_counts[s_name] = count

    for item in settings.employer_boards.split(","):
        if ":" not in item:
            continue
        kind, slug = item.strip().split(":", 1)
        if kind in COLLECTORS:
            board_key = f"{kind}:{slug}"
            items.append({
                "name": f"{slug.replace('-', ' ').title()}",
                "type": kind,
                "slug": slug,
                "board_identifier": board_key,
                "source_url": {
                    "greenhouse": f"https://boards.greenhouse.io/{slug}",
                    "lever": f"https://jobs.lever.co/{slug}",
                    "ashby": f"https://jobs.ashbyhq.com/{slug}"
                }.get(kind, ""),
                "active": True,
                "jobs_collected": source_counts.get(board_key, 0)
            })
    return {"items": items}

@app.get("/api/preferences")
def get_preferences():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM job_preferences LIMIT 1")
        row = cur.fetchone()
        if row:
            d = dict(row)
            for k in ["target_titles", "target_countries", "target_regions", "skills"]:
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    d[k] = []
            return d

    # Default profile preferences
    return {
        "target_titles": [
            "AI Engineer", "Applied AI Engineer", "Agentic AI Engineer",
            "LLM Engineer", "Machine Learning Engineer", "AI Automation Engineer",
            "Full-Stack AI Engineer"
        ],
        "target_countries": [
            "United Kingdom", "Germany", "Netherlands", "Ireland",
            "United States", "Canada", "Australia", "Singapore",
            "Japan", "United Arab Emirates", "Saudi Arabia"
        ],
        "target_regions": ["Europe", "North America", "Asia-Pacific", "Middle East"],
        "skills": [
            "Python", "FastAPI", "LangChain", "LangGraph", "OpenAI",
            "Claude", "Gemini", "RAG", "Multi-Agent", "PyTorch", "Supabase"
        ],
        "minimum_match_score": 70,
        "sponsorship_priority": True,
        "relocation_preference": True,
        "remote_preference": True,
        "daily_notification_limit": 30
    }

@app.put("/api/preferences")
def update_preferences(payload: dict):
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO job_preferences (
            id, target_titles, target_countries, target_regions, skills,
            minimum_match_score, sponsorship_priority, relocation_preference,
            remote_preference, telegram_enabled, email_enabled, daily_notification_limit, updated_at
        ) VALUES ('default', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            target_titles=excluded.target_titles,
            target_countries=excluded.target_countries,
            target_regions=excluded.target_regions,
            skills=excluded.skills,
            minimum_match_score=excluded.minimum_match_score,
            sponsorship_priority=excluded.sponsorship_priority,
            relocation_preference=excluded.relocation_preference,
            remote_preference=excluded.remote_preference,
            telegram_enabled=excluded.telegram_enabled,
            email_enabled=excluded.email_enabled,
            daily_notification_limit=excluded.daily_notification_limit,
            updated_at=excluded.updated_at
        """, (
            json.dumps(payload.get("target_titles", [])),
            json.dumps(payload.get("target_countries", [])),
            json.dumps(payload.get("target_regions", [])),
            json.dumps(payload.get("skills", [])),
            payload.get("minimum_match_score", 70),
            1 if payload.get("sponsorship_priority", True) else 0,
            1 if payload.get("relocation_preference", True) else 0,
            1 if payload.get("remote_preference", True) else 0,
            1 if payload.get("telegram_enabled", False) else 0,
            1 if payload.get("email_enabled", False) else 0,
            payload.get("daily_notification_limit", 30),
            now
        ))
        conn.commit()

    # Mirror to Supabase if available
    db = get_db_client()
    if db:
        try:
            db.table("job_preferences").upsert(payload).execute()
        except Exception:
            pass

    return {"status": "success", "updated_at": now}

@app.get("/api/applications")
def applications():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
        SELECT a.id, a.job_id, a.status, a.applied_at, a.notes, a.created_at,
               j.title, j.company, j.location, j.country, j.match_score, j.sponsorship_status, j.application_url
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        ORDER BY a.created_at DESC
        """)
        rows = cur.fetchall()
        items = []
        for r in rows:
            d = dict(r)
            job_obj = {
                "id": d["job_id"],
                "title": d["title"],
                "company": d["company"],
                "location": d["location"],
                "country": d["country"],
                "match_score": d["match_score"],
                "sponsorship_status": d["sponsorship_status"],
                "application_url": d["application_url"]
            }
            items.append({
                "id": d["id"],
                "job_id": d["job_id"],
                "status": d["status"],
                "applied_at": d["applied_at"],
                "notes": d["notes"],
                "created_at": d["created_at"],
                "jobs": job_obj
            })
        return {"items": items}

@app.post("/api/applications")
def create_application(payload: dict):
    job_id = payload.get("job_id")
    if not job_id:
        raise HTTPException(400, "job_id is required")

    status = payload.get("status", "saved")
    notes = payload.get("notes", "")
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM applications WHERE job_id=?", (job_id,))
        existing = cur.fetchone()
        if existing:
            app_id = existing[0]
            conn.execute("UPDATE applications SET status=?, notes=?, updated_at=? WHERE id=?", (status, notes, now, app_id))
        else:
            app_id = str(uuid.uuid4())
            conn.execute("""
            INSERT INTO applications (id, job_id, status, applied_at, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (app_id, job_id, status, now if status == "applied" else None, notes, now, now))
        conn.commit()

    return {"id": app_id, "job_id": job_id, "status": status}

@app.patch("/api/applications/{application_id}")
def update_application(application_id: str, payload: dict):
    status = payload.get("status")
    notes = payload.get("notes")
    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        if status and notes is not None:
            conn.execute("UPDATE applications SET status=?, notes=?, updated_at=? WHERE id=?", (status, notes, now, application_id))
        elif status:
            conn.execute("UPDATE applications SET status=?, updated_at=? WHERE id=?", (status, now, application_id))
        elif notes is not None:
            conn.execute("UPDATE applications SET notes=?, updated_at=? WHERE id=?", (notes, now, application_id))
        conn.commit()

    return {"status": "success", "id": application_id}

@app.post("/api/collect/run")
async def collect_run(request: Request):
    # Allow localhost or authenticated execution
    peer = request.client.host if request.client else ""
    try:
        is_local = ipaddress.ip_address(peer).is_loopback
    except ValueError:
        is_local = False

    if not is_local:
        raise HTTPException(403, "Collection trigger is available from localhost only")

    if not settings.employer_boards:
        raise HTTPException(503, "Configure EMPLOYER_BOARDS in your environment first.")

    start_time = time.monotonic()
    db = get_db_client()

    summary = {
        "sources": 0,
        "discovered": 0,
        "saved": 0,
        "errors": []
    }

    board_specs = [b.strip() for b in settings.employer_boards.split(",") if ":" in b.strip()]

    for spec in board_specs:
        try:
            kind, slug = spec.split(":", 1)
            collector = COLLECTORS.get(kind)
            if not collector:
                continue

            jobs_data = await collector(slug)
            summary["sources"] += 1
            summary["discovered"] += len(jobs_data)

            for job in jobs_data:
                try:
                    is_new = save_job(db, kind, slug, job)
                    if is_new:
                        summary["saved"] += 1
                except Exception as exc:
                    summary["errors"].append(f"{kind}:{slug} job save error: {str(exc)[:120]}")
        except Exception as exc:
            summary["errors"].append(f"{spec}: {str(exc)[:150]}")
            log.exception(f"Collection failed for source {spec}")

    duration = round(time.monotonic() - start_time, 2)
    summary["duration_seconds"] = duration

    record_job_run_sqlite(
        sources=summary["sources"],
        discovered=summary["discovered"],
        saved=summary["saved"],
        duration=duration,
        errors=summary["errors"],
        status="partial" if summary["errors"] else "completed"
    )

    log.info(
        f"Collection finished: {summary['discovered']} discovered, "
        f"{summary['saved']} new saved, {len(summary['errors'])} errors in {duration}s"
    )
    return summary

@app.post("/api/notifications/test")
async def test_notification():
    items = list_jobs_sqlite(limit=30, sort="match")["items"]
    results = {}
    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:
            sent = await send_telegram(items)
            results["telegram"] = "sent" if sent else "skipped"
        except Exception as e:
            results["telegram"] = f"error: {str(e)}"
    else:
        results["telegram"] = "not configured"

    if settings.smtp_email and settings.smtp_password:
        try:
            sent = send_email(items)
            results["email"] = "sent" if sent else "skipped"
        except Exception as e:
            results["email"] = f"error: {str(e)}"
    else:
        results["email"] = "not configured"

    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
