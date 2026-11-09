"""Independent Discord and email notification providers."""

from app.notifications.email import format_email, send_email
from app.notifications.discord import (
    send_collection_summary,
    send_daily_report,
    send_failure_report,
    send_priority_alerts,
    send_test_message,
)

__all__ = [
    "format_email",
    "send_email",
    "send_collection_summary",
    "send_daily_report",
    "send_failure_report",
    "send_priority_alerts",
    "send_test_message",
]
