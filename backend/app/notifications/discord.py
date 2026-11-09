"""Discord webhook delivery for daily job reports and collection alerts."""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.config import settings

log = logging.getLogger("jobpilot.notifications.discord")
DISCORD_MAX_EMBEDS = 10
REPORT_JOBS_PER_MESSAGE = 3


def _unique_jobs(jobs: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for job in jobs:
        key = job.get("canonical_url") or job.get("application_url") or job.get("id")
        if key and key not in seen:
            seen.add(key)
            unique.append(job)
    return unique


def _job_embed(job: dict) -> dict:
    status = str(job.get("sponsorship_status") or "unverified").lower()
    color = {"confirmed": 0x16A36A, "likely": 0xD49B16}.get(status, 0x64748B)
    location = (", ".join(filter(None, [job.get("location"), job.get("country")])) or "Not listed")[:150]
    skills = (", ".join((job.get("required_skills") or [])[:6]) or "Not specified")[:350]
    description = (job.get("match_explanation") or "").strip()[:250]
    evidence = (job.get("sponsorship_evidence") or "Not confirmed in the vacancy text.").strip()[:350]
    salary = (job.get("salary_text") or "Not published")[:100]
    score = job.get("match_score")

    embed = {
        "title": str(job.get("title") or "Untitled role")[:200],
        "description": f"**{str(job.get('company') or 'Unknown company')[:100]}** · {location}",
        "color": color,
        "fields": [
            {"name": "Match", "value": f"{score if score is not None else 'N/A'}/100", "inline": True},
            {"name": "Sponsorship", "value": status.upper(), "inline": True},
            {"name": "Salary", "value": salary, "inline": True},
            {"name": "Skills", "value": skills, "inline": False},
            {"name": "Sponsorship evidence", "value": evidence or "Not stated", "inline": False},
        ],
    }
    if description:
        embed["fields"].append({"name": "Match notes", "value": description, "inline": False})
    url = job.get("application_url")
    if isinstance(url, str) and url.startswith("https://"):
        embed["url"] = url
    return embed


async def _send_embeds(embeds: list[dict]) -> bool:
    webhook = settings.discord_webhook_url
    if not webhook:
        log.info("Discord delivery skipped: webhook is not configured")
        return False

    async with httpx.AsyncClient(timeout=25) as client:
        for start in range(0, len(embeds), DISCORD_MAX_EMBEDS):
            payload = {"embeds": embeds[start : start + DISCORD_MAX_EMBEDS]}
            for attempt in range(3):
                try:
                    response = await client.post(webhook, json=payload)
                    if response.status_code == 429:
                        try:
                            wait = float(response.json().get("retry_after", 1))
                        except (ValueError, TypeError):
                            wait = 1
                        if attempt < 2:
                            await asyncio.sleep(min(max(wait, 0.25), 10))
                            continue
                    if response.status_code in (408, 500, 502, 503, 504) and attempt < 2:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    break
                except httpx.TimeoutException:
                    if attempt == 2:
                        log.warning("Discord delivery timed out")
                        raise RuntimeError("Discord delivery failed") from None
                    await asyncio.sleep(0.5 * (attempt + 1))
                except httpx.HTTPError as exc:
                    log.warning("Discord webhook delivery failed (%s)", type(exc).__name__)
                    raise RuntimeError("Discord delivery failed") from None
            else:
                return False

    log.info("Discord delivered %d embed(s)", len(embeds))
    return True


async def send_daily_report(jobs: list[dict]) -> bool:
    selected = _unique_jobs(jobs)[:30]
    if not selected:
        log.info("Discord daily report skipped: no jobs to report")
        return False

    confirmed = sum(j.get("sponsorship_status") == "confirmed" for j in selected)
    likely = sum(j.get("sponsorship_status") == "likely" for j in selected)
    embeds = []
    for start in range(0, len(selected), REPORT_JOBS_PER_MESSAGE):
        group = selected[start : start + REPORT_JOBS_PER_MESSAGE]
        if start == 0:
            embeds.append({
                "title": "Global AI JobPilot · Daily International AI Job Report",
                "description": (
                    f"{datetime.now(timezone.utc):%d %B %Y} · {len(selected)} selected jobs\n"
                    f"Confirmed sponsorship: {confirmed} · Likely: {likely}\n"
                    "Unverified sponsorship is not a guarantee. Check each employer's original listing."
                ),
                "color": 0x087D88,
            })
        embeds.extend(_job_embed(job) for job in group)
    return await _send_embeds(embeds)


async def send_priority_alerts(jobs: list[dict]) -> bool:
    priority = [
        job for job in _unique_jobs(jobs)
        if (job.get("match_score") or 0) >= 90 or job.get("sponsorship_status") == "confirmed"
    ][:3]
    if not priority:
        return False
    embeds = [{
        "title": "High-priority AI job alerts",
        "description": "High match score or confirmed sponsorship. Verify details on the employer's listing.",
        "color": 0x16A36A,
    }]
    embeds.extend(_job_embed(job) for job in priority)
    return await _send_embeds(embeds)


async def send_collection_summary(summary: dict) -> bool:
    errors = summary.get("errors") or []
    status = "Partial" if errors else "Completed"
    return await _send_embeds([{
        "title": f"Daily collection {status.lower()}",
        "description": (
            f"Sources: {summary.get('sources', 0)} · Discovered: {summary.get('discovered', 0)} · "
            f"New: {summary.get('saved', 0)} · Duration: {summary.get('duration_seconds', 0)}s"
        ),
        "color": 0xD49B16 if errors else 0x16A36A,
    }])


async def send_failure_report(errors: list[str]) -> bool:
    if not errors:
        return False
    embeds = []
    for start in range(0, len(errors), 8):
        block = "\n".join(f"• {str(error)[:450]}" for error in errors[start : start + 8])
        embeds.append({
            "title": "JobPilot collection or delivery failures",
            "description": block[:4000],
            "color": 0xD34848,
        })
    return await _send_embeds(embeds)


async def send_test_message() -> bool:
    return await _send_embeds([{
        "title": "Global AI JobPilot · Discord connection test",
        "description": "Discord webhook delivery is configured successfully.",
        "color": 0x087D88,
    }])
