"""
Ports (driven interfaces) for the vulnctl application core.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class AffectedInfo:
    """A single affected vendor/product pair."""

    vendor: str
    product: str
    version: Optional[str] = None
    cpe: Optional[list[str]] = None


@dataclass
class CVEInfo:
    """A CVE summary returned by the CVE store."""

    cve_id: str
    status: str
    title: str
    date_updated: Optional[datetime]
    affected: Optional[list[AffectedInfo]] = None


class RecentCVEStorePort(Protocol):
    """Interface for querying recent CVEs (user, HTTP). Days window only."""

    async def list(self, days: int) -> list[CVEInfo]:
        """
        Fetch CVEs from the last N days (1–3).

        Args:
            days: Number of days to look back. Server computes since = now - days.

        Returns:
            CVEInfo list ordered by date_updated DESC.
        """
        ...
