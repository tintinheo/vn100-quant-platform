"""Presentation model for governed synchronization state."""
from __future__ import annotations

from dataclasses import dataclass

from vnquant.data.source_sync import SyncReport


@dataclass(frozen=True)
class SyncStatusView:
    state: str
    severity: str
    primary_message: str
    next_action: str | None
    details: str


def synchronization_status_view(report: SyncReport) -> SyncStatusView:
    """Translate the sync contract without conflating fetch and DQ failures."""
    if report.status == "NO_ADMITTED_PROVIDER":
        state = "NO_ADMITTED_PROVIDER"
        primary = "NO_ADMITTED_PROVIDER — no provider is eligible for real-data synchronization."
    elif report.mode == "DEGRADED_CACHED_DATA":
        state, primary = "DEGRADED_CACHED_DATA", "DEGRADED_CACHED_DATA — provider synchronization failed; accepted cached data is retained."
    elif report.mode == "STALE" or report.status == "CACHE_STALE":
        state, primary = "STALE", "STALE — accepted cached data is older than the expected market session."
    elif report.mode == "FAILED" or report.status == "SYNC_FAILED":
        state, primary = "FAILED", f"FAILED — {report.failure_reason or 'synchronization did not complete.'}"
    else:
        state, primary = "FRESH", "FRESH — synchronization completed with accepted canonical data."

    details = (
        f"provider: {report.provider_id or 'none'}; "
        f"data as of: {report.data_as_of or 'unavailable'}; "
        f"last sync: {report.last_sync_at or 'never'}; "
        f"DQ: {report.dq_status}; "
        f"cache accepted: {'yes' if report.cache_accepted else 'no'}; "
        f"actionable recommendations: {'allowed' if report.actionable else 'blocked'}"
    )
    severity = "success" if state == "FRESH" else "warning" if report.cache_accepted else "error"
    return SyncStatusView(state, severity, primary, report.next_action, details)
