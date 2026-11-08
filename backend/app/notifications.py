"""
Notifications Module: Telegram Bot & SMTP Email Delivery
Generates structured daily intelligence reports for international AI vacancies.
"""
import html
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
import httpx
from app.config import settings

def format_telegram(jobs: list[dict]) -> str:
    today_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    selected_count = min(len(jobs), 30)
    lines = [
        "🌐 GLOBAL AI JOBPILOT — DAILY REPORT",
        f"📅 Date: {today_str}",
        f"🎯 Selected Matched Jobs: {selected_count}",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]

    for i, j in enumerate(jobs[:30], 1):
        title = j.get("title", "Untitled")
        company = j.get("company", "Unknown")
        loc = [j.get("location"), j.get("country")].copy()
        loc_str = ", ".join(filter(None, loc)) or "Location not specified"
        score = j.get("match_score", "—")
        sponsorship = str(j.get("sponsorship_status", "unverified")).upper()
        salary = j.get("salary_text")
        skills = ", ".join((j.get("required_skills") or [])[:5]) or "AI / ML"
        reason = j.get("match_explanation") or "Matched with candidate technical profile."
        url = j.get("application_url", "")

        block = [
            f"{i}. 💼 {title}",
            f"🏢 Company: {company}",
            f"📍 Location: {loc_str}",
            f"⚡ Match: {score}/100",
            f"🛂 Sponsorship: {sponsorship}"
        ]
        if salary:
            block.append(f"💰 Salary: {salary}")
        block.extend([
            f"🛠 Skills: {skills}",
            f"💡 Reason: {reason}",
            f"🔗 Apply: {url}",
            ""
        ])
        lines.extend(block)

    return "\n".join(lines)

def format_email(jobs: list[dict]) -> str:
    today_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    confirmed = [j for j in jobs if j.get("sponsorship_status") == "confirmed"]
    likely = [j for j in jobs if j.get("sponsorship_status") == "likely"]
    others = [j for j in jobs if j.get("sponsorship_status") not in ("confirmed", "likely")]

    def render_cards(card_jobs: list[dict]) -> str:
        if not card_jobs:
            return "<p style='color: #718096; font-size: 13px;'>No vacancies in this category today.</p>"
        out = []
        for j in card_jobs:
            title = html.escape(j.get("title", "Untitled"))
            company = html.escape(j.get("company", "Unknown"))
            loc = html.escape(j.get("location") or j.get("country") or "Location not listed")
            score = j.get("match_score", "—")
            status = html.escape(str(j.get("sponsorship_status", "unverified")).upper())
            evidence = html.escape(j.get("sponsorship_evidence") or "No vacancy-specific sponsorship text detected.")
            reason = html.escape(j.get("match_explanation") or "Matched candidate technical profile.")
            skills = ", ".join(html.escape(s) for s in (j.get("required_skills") or [])[:6]) or "AI / ML"
            url = html.escape(j.get("application_url", ""), quote=True)
            salary = html.escape(j.get("salary_text") or "")

            salary_html = f"<div style='margin-top: 4px; font-size: 12px; color: #2b6cb0;'><strong>💰 Salary:</strong> {salary}</div>" if salary else ""

            badge_color = "#00a875" if status == "CONFIRMED" else "#b7791f" if status == "LIKELY" else "#4a5568"
            badge_bg = "#e6faf2" if status == "CONFIRMED" else "#fefcbf" if status == "LIKELY" else "#edf2f7"

            out.append(f"""
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <h3 style="margin: 0 0 4px 0; font-size: 16px; color: #1a202c; font-family: sans-serif;">{title}</h3>
                        <div style="color: #4a5568; font-size: 13px; font-weight: 600;">{company} &bull; 📍 {loc}</div>
                    </div>
                    <div style="text-align: right;">
                        <span style="background: {badge_bg}; color: {badge_color}; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 12px; display: inline-block;">{status}</span>
                        <div style="font-size: 14px; font-weight: 800; color: #2b6cb0; margin-top: 4px;">{score}% Match</div>
                    </div>
                </div>
                {salary_html}
                <div style="background: #f7fafc; border-left: 3px solid #3182ce; padding: 8px 12px; margin: 10px 0; font-size: 12px; color: #4a5568;">
                    <strong>Sponsorship Evidence:</strong> {evidence}
                </div>
                <div style="font-size: 12px; color: #4a5568; margin-bottom: 6px;">
                    <strong>Matched Skills:</strong> {skills}
                </div>
                <div style="font-size: 12px; color: #718096; margin-bottom: 12px;">
                    <strong>Why You Match:</strong> {reason}
                </div>
                <div>
                    <a href="{url}" target="_blank" style="background: #00a875; color: #ffffff; text-decoration: none; font-size: 12px; font-weight: 700; padding: 8px 16px; border-radius: 6px; display: inline-block;">Apply Directly on Employer Site &rarr;</a>
                </div>
            </div>
            """)
        return "".join(out)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Global AI JobPilot Daily Intelligence</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f7fc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f7fc; padding: 24px 0;">
            <tr>
                <td align="center">
                    <table width="680" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.06);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #07152e, #0c2b55); padding: 32px; color: #ffffff; text-align: left;">
                                <div style="font-size: 11px; font-weight: 700; letter-spacing: 1.5px; color: #00c5a5; margin-bottom: 6px;">GLOBAL AI JOBPILOT</div>
                                <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Daily Worldwide AI Opportunities</h1>
                                <p style="margin: 0; font-size: 13px; color: #cbd5e0;">Report for {today_str} &bull; Candidate: Talha Aftab (Rawalpindi, Pakistan)</p>
                            </td>
                        </tr>
                        <!-- Summary Bar -->
                        <tr>
                            <td style="background-color: #edf2f7; padding: 14px 32px; border-bottom: 1px solid #e2e8f0;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="font-size: 12px; color: #4a5568;">
                                            <strong>{len(jobs)}</strong> Selected Jobs &bull; 
                                            <strong style="color: #00a875;">{len(confirmed)}</strong> Confirmed Sponsorship &bull; 
                                            <strong style="color: #b7791f;">{len(likely)}</strong> Likely Sponsorship
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <!-- Body Content -->
                        <tr>
                            <td style="padding: 28px 32px;">
                                {f'<h2 style="font-size: 16px; color: #1a202c; margin: 0 0 14px 0; border-bottom: 2px solid #00a875; padding-bottom: 6px;">🎯 Confirmed Visa Sponsorship ({len(confirmed)})</h2>' + render_cards(confirmed) if confirmed else ''}
                                {f'<h2 style="font-size: 16px; color: #1a202c; margin: 24px 0 14px 0; border-bottom: 2px solid #b7791f; padding-bottom: 6px;">⚡ Likely Visa Sponsorship ({len(likely)})</h2>' + render_cards(likely) if likely else ''}
                                {f'<h2 style="font-size: 16px; color: #1a202c; margin: 24px 0 14px 0; border-bottom: 2px solid #4a5568; padding-bottom: 6px;">🌐 Other Matched International Roles ({len(others)})</h2>' + render_cards(others) if others else ''}
                            </td>
                        </tr>
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f7fafc; padding: 20px 32px; border-top: 1px solid #edf2f7; font-size: 11px; color: #a0aec0; text-align: center;">
                                Global AI JobPilot &bull; Automated Daily Run &bull; Clean, Authorized Public ATS Job Feeds Only
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

async def send_telegram(jobs: list[dict]) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    text = format_telegram(jobs)
    async with httpx.AsyncClient(timeout=20) as client:
        # Split across 3900 character chunks to respect Telegram message limits
        for part in [text[i:i + 3900] for i in range(0, len(text), 3900)]:
            r = await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": part,
                    "disable_web_page_preview": True
                }
            )
            r.raise_for_status()
    return True

def send_email(jobs: list[dict]) -> bool:
    if not settings.smtp_email or not settings.smtp_password:
        return False
    msg = EmailMessage()
    msg["Subject"] = f"Global AI JobPilot — Daily Report ({datetime.now(timezone.utc).strftime('%d %b %Y')})"
    msg["From"] = settings.smtp_email
    msg["To"] = settings.smtp_email
    msg.set_content("Open this message in an HTML email client to view the full intelligence report.")
    msg.add_alternative(format_email(jobs), subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=25) as server:
        server.starttls()
        server.login(settings.smtp_email, settings.smtp_password)
        server.send_message(msg)
    return True
