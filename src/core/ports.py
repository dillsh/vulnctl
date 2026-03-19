"""
Ports (driven interfaces) for the vulnctl application core.

These Protocol classes define what the core needs from infrastructure.
Adapters implement them; the core never imports adapters directly.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Protocol


@dataclass
class CollectionResult:
    """Result returned by a triggered CVE collection."""
    workflow_id: str


@dataclass
class ScheduleInfo:
    """Summary of a single Temporal Schedule."""
    schedule_id: str
    cron: str
    next_run: str | None


class CollectorPort(Protocol):
    """Interface for triggering CVE collection on cve-collector."""

    async def trigger(self, start_time: int, end_time: int) -> CollectionResult:
        """
        Trigger a collection run.

        Args:
            start_time: Unix timestamp (seconds) for the collection window start.
            end_time:   Unix timestamp (seconds) for the collection window end (0 = not set).

        Returns:
            CollectionResult with the started workflow ID.
        """
        ...


@dataclass
class AffectedInfo:
    """A single affected vendor/product pair."""
    vendor: str
    product: str


@dataclass
class CVEInfo:
    """A CVE summary returned by the CVE store."""
    cve_id: str
    status: str
    title: str
    date_updated: Optional[datetime]
    affected: Optional[list[AffectedInfo]] = None


class CVEStorePort(Protocol):
    """Interface for querying CVEs from cve-core."""

    async def list(
        self,
        start_time: datetime,
        end_time: Optional[datetime],
    ) -> list[CVEInfo]:
        """
        Fetch CVEs with date_updated within [start_time, end_time].

        Args:
            start_time: Lower bound on date_updated (inclusive).
            end_time:   Upper bound on date_updated (inclusive). None = no upper bound.

        Returns:
            CVEInfo list ordered by date_updated DESC.
        """
        ...


class SchedulerPort(Protocol):
    """Interface for managing Temporal Schedules."""

    async def create(self, schedule_id: str, cron: str) -> None:
        """Create a new recurring schedule."""
        ...

    async def list(self) -> list[ScheduleInfo]:
        """Return all existing schedules."""
        ...

    async def delete(self, schedule_id: str) -> None:
        """Delete a schedule by ID."""
        ...
