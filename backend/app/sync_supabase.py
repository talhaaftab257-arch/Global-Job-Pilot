import json
import logging
import sqlite3
import httpx
from app.config import settings
from app.database import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sync_supabase")

def sync():
    api_key = settings.supabase_admin_key
    if not settings.supabase_url or not api_key:
        log.error("Supabase credentials not configured in .env")
        return

    headers = {
        "apikey": api_key,
        "Content-Type": "application/json",
        "User-Agent": "GlobalAIJobPilot/1.0",
        "Prefer": "resolution=merge-duplicates"
    }
    if not api_key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {api_key}"

    url = f"{settings.supabase_url.rstrip('/')}/rest/v1"

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Sync job_sources
        cur.execute("SELECT * FROM job_sources")
        sources = [dict(r) for r in cur.fetchall()]
        log.info(f"Syncing {len(sources)} sources to Supabase...")
        for s in sources:
            s_data = {
                "id": s["id"],
                "name": s["name"],
                "source_type": s["source_type"],
                "board_identifier": s["board_identifier"],
                "source_url": s.get("source_url"),
                "active": bool(s.get("active", 1)),
                "last_collected_at": s.get("last_collected_at"),
                "created_at": s.get("created_at")
            }
            try:
                r = httpx.post(f"{url}/job_sources", headers=headers, json=s_data, timeout=15)
                if r.status_code not in (200, 201, 204):
                    log.warning(f"Source {s['name']} sync: {r.status_code} {r.text[:100]}")
            except Exception as e:
                log.warning(f"Error syncing source {s['name']}: {e}")

        # 2. Sync jobs in batches of 100
        cur.execute("SELECT * FROM jobs")
        all_jobs = []
        for r in cur.fetchall():
            d = dict(r)
            try:
                d["required_skills"] = json.loads(d.get("required_skills") or "[]")
            except Exception:
                d["required_skills"] = []
            try:
                d["raw_source_data"] = json.loads(d.get("raw_source_data") or "{}")
            except Exception:
                d["raw_source_data"] = {}
            d["relocation_support"] = bool(d.get("relocation_support"))
            d["employer_sponsor_verified"] = bool(d.get("employer_sponsor_verified"))
            if "remote_type" in d:
                d.pop("remote_type", None)
            all_jobs.append(d)

        log.info(f"Syncing {len(all_jobs)} jobs to Supabase...")
        batch_size = 100
        synced_count = 0
        for i in range(0, len(all_jobs), batch_size):
            batch = all_jobs[i:i + batch_size]
            try:
                r = httpx.post(f"{url}/jobs", headers=headers, json=batch, timeout=30)
                if r.status_code in (200, 201, 204):
                    synced_count += len(batch)
                    log.info(f"Progress: {synced_count}/{len(all_jobs)} jobs synced...")
                else:
                    log.warning(f"Batch {i} failed: {r.status_code} {r.text[:150]}")
            except Exception as e:
                log.error(f"Error uploading batch {i}: {e}")

        log.info(f"Sync complete! {synced_count} jobs synced to Supabase PostgreSQL.")

if __name__ == "__main__":
    sync()
