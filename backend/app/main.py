import logging
import time
import ipaddress
import json
import sqlite3
import uuid
import secrets
from datetime import datetime, timezone
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.collectors.public_ats import COLLECTORS
from app.database import (
    get_db_client, save_job, list_jobs_sqlite, get_job_sqlite,
    record_job_run_sqlite, DB_PATH
)
from app.notifications import send_email, send_test_message

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


@app.middleware("http")
async def authenticate_api_requests(request: Request, call_next):
    if not request.url.path.startswith("/api/") or request.url.path == "/api/health" or request.method == "OPTIONS":
        return await call_next(request)

    peer = request.client.host if request.client else ""
    is_local = False
    try:
        is_local = ipaddress.ip_address(peer).is_loopback
    except ValueError:
        is_local = peer in ("testclient", "localhost", "127.0.0.1", "")

    if settings.local_auth_bypass or is_local:
        request.state.user_id = "local"
        return await call_next(request)

    public_prefixes = ("/api/jobs", "/api/sources", "/api/analytics")
    if request.method == "GET" and (
        any(request.url.path.startswith(prefix) for prefix in public_prefixes)
        or request.url.path == "/api/preferences"
    ):
        request.state.user_id = "local" if is_local else "anonymous"
        return await call_next(request)

    if settings.supabase_url and settings.supabase_admin_key:
        authorization = request.headers.get("authorization", "")
        token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
        if not token:
            return JSONResponse({"detail": "Sign in to use this API."}, status_code=401)
        try:
            auth_response = get_db_client().auth.get_user(token)
            user = getattr(auth_response, "user", None)
            if not user or not user.id:
                return JSONResponse({"detail": "Invalid or expired session."}, status_code=401)
            request.state.user_id = str(user.id)
        except Exception:
            return JSONResponse({"detail": "Invalid or expired session."}, status_code=401)
    else:
        return JSONResponse({"detail": "Supabase authentication is not configured."}, status_code=503)

    return await call_next(request)

@app.get("/api/health")
def health():
    db = get_db_client()
    configured_sources = [
        item.strip() for item in settings.employer_boards.split(",")
        if ":" in item.strip()
    ]
    local_jobs_count = 0
    database_reachable = False
    if db:
        try:
            count_result = db.table("jobs").select("id", count="exact").eq("status", "open").limit(1).execute()
            local_jobs_count = count_result.count or 0
            database_reachable = True
        except Exception as exc:
            log.warning("Supabase health query failed: %s", type(exc).__name__)
    else:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM jobs WHERE status='open'")
            local_jobs_count = cur.fetchone()[0]

    return {
        "status": "ok",
        "database_configured": bool(settings.supabase_url and settings.supabase_admin_key),
        "database_reachable": database_reachable if db else False,
        "sources_configured": len(configured_sources),
        "total_jobs": local_jobs_count,
        "ai_engine": "Groq configured" if settings.groq_api_key else "rule-based heuristic active",
        "groq_configured": bool(settings.groq_api_key)
    }

@app.get("/api/jobs")
def jobs(
    request: Request = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sponsorship: str | None = None,
    country: str | None = None,
    query: str | None = None,
    sort: str = "match"
):
    user_id = getattr(request.state, "user_id", "local") if request else "local"
    if user_id == "local" or (DB_PATH.exists() and not os.getenv("VERCEL")):
        return list_jobs_sqlite(
            limit=limit,
            offset=offset,
            sponsorship=sponsorship,
            country=country,
            query=query,
            sort=sort
        )

    db = get_db_client()
    if db:
        try:
            cols = (
                "id,source_id,source_name,external_id,canonical_url,title,company,location,country,"
                "salary_text,application_url,posted_at,required_skills,sponsorship_status,sponsorship_evidence,"
                "relocation_support,relocation_evidence,match_score,technical_score,role_score,ai_relevance_score,"
                "experience_score,sponsorship_score,location_score,recency_score,match_explanation,status,remote_type"
            )
            q = db.table("jobs").select(cols).eq("status", "open")
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
                        if query.lower() in f"{j.get('title','')} {j.get('company','')} {j.get('location','')} {j.get('external_id','')}".lower()
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
def featured(request: Request = None):
    return jobs(request=request, limit=30, offset=0, sort="match")

@app.get("/api/jobs/sponsorship")
def sponsorship(status: str | None = None, request: Request = None):
    return jobs(request=request, limit=250, offset=0, sponsorship=status)

@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str, request: Request = None):
    user_id = getattr(request.state, "user_id", "local") if request else "local"
    if user_id == "local" or (DB_PATH.exists() and not os.getenv("VERCEL")):
        job = get_job_sqlite(job_id)
        if job:
            return job

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


def _analytics_jobs(use_local: bool = False) -> list[dict]:
    db = get_db_client()
    if not db or use_local:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT sponsorship_status, match_score, country FROM jobs WHERE status='open'")
            return [dict(r) for r in cur.fetchall()]

    jobs_data = []
    try:
        offset = 0
        while offset < 50000:
            response = (
                db.table("jobs")
                .select("sponsorship_status,match_score,country")
                .eq("status", "open")
                .range(offset, offset + 999)
                .execute()
            )
            page = response.data or []
            jobs_data.extend(page)
            if len(page) < 1000:
                break
            offset += 1000
        return jobs_data
    except Exception as exc:
        log.warning("Supabase analytics query failed: %s; falling back to local SQLite", type(exc).__name__)
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT sponsorship_status, match_score, country FROM jobs WHERE status='open'")
            return [dict(r) for r in cur.fetchall()]

@app.post("/api/ai/analyze-job/{job_id}")
async def analyze_job_with_groq(job_id: str):
    if not settings.groq_api_key:
        raise HTTPException(503, "Groq is not configured. Add GROQ_API_KEY to the backend .env file.")

    job = get_job_sqlite(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    prompt = (
        "Assess this vacancy for a candidate based in Rawalpindi, Pakistan: Lead Data Scientist / AI Engineer; "
        "skills include Python, FastAPI, LangGraph, RAG, multi-agent systems, PyTorch, Docker, SQL and Supabase. "
        "Give a concise evidence-based assessment with: fit (0-100), strongest overlaps, gaps/risks, "
        "and visa/relocation evidence. Do not infer sponsorship if the description does not explicitly support it. "
        "Clearly label unknown details.\n\n"
        f"Title: {job.get('title')}\nCompany: {job.get('company')}\nLocation: {job.get('location')}\n"
        f"Existing sponsorship classification: {job.get('sponsorship_status')}\n"
        f"Description: {(job.get('description') or '')[:10000]}"
    )

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                json={
                    "model": settings.groq_model,
                    "messages": [
                        {"role": "system", "content": "You are a careful international AI careers analyst. Use only evidence in the supplied job description."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 600
                }
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
        return {"analysis": result, "model": settings.groq_model}
    except httpx.HTTPStatusError as exc:
        log.warning("Groq analysis request failed with status %s", exc.response.status_code)
        raise HTTPException(502, "Groq analysis request failed. Check the backend key, model, and account limits.") from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
        log.warning("Groq analysis request failed: %s", type(exc).__name__)
        raise HTTPException(502, "Could not get an analysis from Groq.") from exc

@app.get("/api/analytics/overview")
def overview(request: Request):
    items = _analytics_jobs(request.state.user_id == "local")
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
def countries(request: Request):
    items = _analytics_jobs(request.state.user_id == "local")
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
    # Use the shared database in deployed environments; SQLite is only the local fallback.
    source_counts = {}
    db = get_db_client()
    if db:
        for item in settings.employer_boards.split(","):
            if ":" not in item:
                continue
            kind, slug = item.strip().split(":", 1)
            source_name = f"{kind}:{slug}"
            try:
                result = db.table("jobs").select("id", count="exact").eq("source_name", source_name).eq("status", "open").limit(1).execute()
                source_counts[source_name] = result.count or 0
            except Exception as exc:
                log.warning("Supabase source count failed: %s", type(exc).__name__)
    else:
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

def _default_preferences() -> dict:
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


@app.get("/api/preferences")
def get_preferences(request: Request):
    db = get_db_client()
    if db and request.state.user_id != "local":
        try:
            result = db.table("job_preferences").select("*").eq("user_id", request.state.user_id).maybe_single().execute()
            if result.data:
                return result.data
            return _default_preferences()
        except Exception as exc:
            log.warning("Supabase preferences read failed: %s", type(exc).__name__)
            raise HTTPException(503, "Preferences storage is unavailable.") from exc

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

    return _default_preferences()

@app.put("/api/preferences")
def update_preferences(payload: dict, request: Request):
    now = datetime.now(timezone.utc).isoformat()
    db = get_db_client()
    if db and request.state.user_id != "local":
        preference = {
            "user_id": request.state.user_id,
            "target_titles": payload.get("target_titles", []),
            "target_countries": payload.get("target_countries", []),
            "target_regions": payload.get("target_regions", []),
            "skills": payload.get("skills", []),
            "minimum_match_score": payload.get("minimum_match_score", 70),
            "sponsorship_priority": payload.get("sponsorship_priority", True),
            "relocation_preference": payload.get("relocation_preference", True),
            "remote_preference": payload.get("remote_preference", True),
            "discord_enabled": payload.get("discord_enabled", False),
            "email_enabled": payload.get("email_enabled", False),
            "daily_notification_limit": payload.get("daily_notification_limit", 30),
            "updated_at": now,
        }
        try:
            db.table("job_preferences").upsert(preference, on_conflict="user_id").execute()
            return {"status": "success", "updated_at": now}
        except Exception as exc:
            log.warning("Supabase preferences write failed: %s", type(exc).__name__)
            raise HTTPException(503, "Preferences could not be saved.") from exc

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO job_preferences (
            id, target_titles, target_countries, target_regions, skills,
            minimum_match_score, sponsorship_priority, relocation_preference,
            remote_preference, discord_enabled, email_enabled, daily_notification_limit, updated_at
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
            discord_enabled=excluded.discord_enabled,
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
            1 if payload.get("discord_enabled", False) else 0,
            1 if payload.get("email_enabled", False) else 0,
            payload.get("daily_notification_limit", 30),
            now
        ))
        conn.commit()

    return {"status": "success", "updated_at": now}

@app.get("/api/applications")
def applications(request: Request):
    db = get_db_client()
    if db and request.state.user_id != "local":
        try:
            result = (
                db.table("applications")
                .select("id,job_id,status,applied_at,notes,created_at,jobs(title,company,location,country,match_score,sponsorship_status,application_url)")
                .eq("user_id", request.state.user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return {"items": result.data or []}
        except Exception as exc:
            log.warning("Supabase application list failed: %s", type(exc).__name__)
            raise HTTPException(503, "Applications storage is unavailable.") from exc

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
def create_application(payload: dict, request: Request):
    job_id = payload.get("job_id")
    if not job_id:
        raise HTTPException(400, "job_id is required")

    status = payload.get("status", "saved")
    notes = payload.get("notes", "")
    now = datetime.now(timezone.utc).isoformat()

    db = get_db_client()
    if db and request.state.user_id != "local":
        application = {
            "user_id": request.state.user_id,
            "job_id": job_id,
            "status": status,
            "applied_at": now if status == "applied" else None,
            "notes": notes,
            "updated_at": now,
        }
        try:
            result = db.table("applications").upsert(application, on_conflict="user_id,job_id").select("id,job_id,status").execute()
            saved = (result.data or [{}])[0]
            return {"id": saved.get("id"), "job_id": job_id, "status": status}
        except Exception as exc:
            log.warning("Supabase application save failed: %s", type(exc).__name__)
            raise HTTPException(503, "Application could not be saved.") from exc

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
def update_application(application_id: str, payload: dict, request: Request):
    status = payload.get("status")
    notes = payload.get("notes")
    now = datetime.now(timezone.utc).isoformat()

    db = get_db_client()
    if db and request.state.user_id != "local":
        changes = {"updated_at": now}
        if status:
            changes["status"] = status
            if status == "applied":
                changes["applied_at"] = now
        if notes is not None:
            changes["notes"] = notes
        try:
            result = db.table("applications").update(changes).eq("id", application_id).eq("user_id", request.state.user_id).select("id").execute()
            if not result.data:
                raise HTTPException(404, "Application not found")
            return {"status": "success", "id": application_id}
        except HTTPException:
            raise
        except Exception as exc:
            log.warning("Supabase application update failed: %s", type(exc).__name__)
            raise HTTPException(503, "Application could not be updated.") from exc

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
    _require_admin_request(request)

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
async def test_notification(request: Request):
    _require_admin_request(request)
    items = list_jobs_sqlite(limit=30, sort="match")["items"]
    results = {}
    if settings.discord_webhook_url:
        try:
            sent = await send_test_message()
            results["discord"] = "sent" if sent else "skipped"
        except Exception as exc:
            log.warning("Discord test notification failed: %s", type(exc).__name__)
            results["discord"] = "delivery failed; check backend logs"
    else:
        results["discord"] = "not configured"

    if settings.smtp_email and settings.smtp_password:
        try:
            sent = send_email(items)
            results["email"] = "sent" if sent else "skipped"
        except Exception as exc:
            log.warning("Email test notification failed: %s", type(exc).__name__)
            results["email"] = "delivery failed; check backend logs"
    else:
        results["email"] = "not configured"

    return results


def _require_admin_request(request: Request) -> None:
    if settings.admin_api_token:
        provided = request.headers.get("x-admin-token", "")
        if not secrets.compare_digest(provided, settings.admin_api_token):
            raise HTTPException(403, "Administrative authorization required")
        return

    peer = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(peer).is_loopback:
            return
    except ValueError:
        pass
    raise HTTPException(403, "Administrative authorization required")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
