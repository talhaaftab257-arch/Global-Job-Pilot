import asyncio
import logging
import time
from datetime import datetime, timezone
from app.config import settings
from app.collectors.public_ats import COLLECTORS
from app.database import get_db_client, save_job, record_job_run_sqlite, list_jobs_sqlite
from app.notifications import (
    send_collection_summary,
    send_daily_report,
    send_email,
    send_failure_report,
    send_priority_alerts,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("jobpilot.daily")

async def run_daily():
    if not settings.employer_boards:
        log.warning("No EMPLOYER_BOARDS configured. Exiting.")
        return

    start_time = time.monotonic()
    db = get_db_client()
    found = []
    errors = []
    sources_count = 0

    specs = [s.strip() for s in settings.employer_boards.split(",") if ":" in s.strip()]

    for spec in specs:
        try:
            kind, slug = spec.split(":", 1)
            collector = COLLECTORS.get(kind)
            if not collector:
                continue

            items = await collector(slug)
            sources_count += 1
            for job in items:
                save_job(db, kind, slug, job)
                found.append(job)
        except Exception as exc:
            errors.append(f"{spec}: {str(exc)[:180]}")
            log.exception(f"Collector failed for {spec}")

    # Deduplicate in-memory by canonical URL
    unique_map = {j["canonical_url"]: j for j in found}
    all_jobs = list(unique_map.values())

    # If this run was empty (e.g. rate limit), pull latest stored jobs
    if not all_jobs:
        all_jobs = list_jobs_sqlite(limit=100, sort="match")["items"]

    # Rank: confirmed first, then likely, then by match score descending
    status_priority = {"confirmed": 0, "likely": 1, "unverified": 2, "unavailable": 3}
    ranked = sorted(
        all_jobs,
        key=lambda j: (status_priority.get(j.get("sponsorship_status", "unverified"), 3), -(j.get("match_score") or 0))
    )[:30]

    # Each provider is isolated so delivery failures never prevent email delivery.
    delivery_report = []
    try:
        sent = await send_daily_report(ranked)
        delivery_report.append({"channel": "discord", "status": "sent" if sent else "skipped"})
    except Exception as exc:
        delivery_report.append({"channel": "discord", "status": "failed", "error": type(exc).__name__})

    try:
        await send_priority_alerts(ranked)
    except Exception as exc:
        delivery_report.append({"channel": "discord_priority_alerts", "status": "failed", "error": type(exc).__name__})

    try:
        summary_for_notice = {
            "sources": sources_count,
            "discovered": len(found),
            "saved": len(found),
            "duration_seconds": round(time.monotonic() - start_time, 2),
            "errors": errors,
        }
        await send_collection_summary(summary_for_notice)
        if errors:
            await send_failure_report(errors)
    except Exception as exc:
        delivery_report.append({"channel": "discord_status", "status": "failed", "error": type(exc).__name__})

    try:
        email_sent = await asyncio.to_thread(send_email, ranked)
        delivery_report.append({"channel": "email", "status": "sent" if email_sent else "skipped"})
    except Exception as exc:
        delivery_report.append({"channel": "email", "status": "failed", "error": str(exc)[:180]})

    duration = round(time.monotonic() - start_time, 2)

    # Record run locally
    record_job_run_sqlite(
        sources=sources_count,
        discovered=len(found),
        saved=len(found),
        duration=duration,
        errors=errors + delivery_report,
        status="partial" if errors else "completed"
    )

    # Also record to Supabase if available
    if db:
        try:
            db.table("job_runs").insert({
                "status": "partial" if errors else "completed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "sources_processed": sources_count,
                "jobs_discovered": len(found),
                "jobs_matched": len(ranked),
                "jobs_saved": len(found),
                "errors": errors + delivery_report,
                "duration_seconds": duration
            }).execute()
        except Exception:
            pass

    log.info(
        f"Daily job run completed: {len(found)} discovered, "
        f"{len(ranked)} selected for report, {len(errors)} source errors in {duration}s"
    )

if __name__ == "__main__":
    asyncio.run(run_daily())
