"""
Application use cases — pure business logic, no framework dependencies.

Each use case accepts a port (interface) in its constructor and calls it.
"""

from datetime import datetime, timezone

from src.core.ports import CVEInfo, CVEStorePort, CollectionResult, CollectorPort, ScheduleInfo, SchedulerPort


class TriggerCollection:
    """
    Trigger a one-off CVE collection run via cve-collector.

    Converts human-friendly ISO date strings to Unix timestamps and
    delegates to CollectorPort.
    """

    def __init__(self, collector: CollectorPort) -> None:
        self._collector = collector

    async def execute(self, since: str, until: str | None) -> CollectionResult:
        """
        Args:
            since: ISO 8601 date/datetime string, e.g. "2024-01-01".
            until: ISO 8601 date/datetime string or None (= open end).

        Returns:
            CollectionResult with the started Temporal workflow ID.
        """
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
        start_time = int(since_dt.timestamp())

        end_time = 0
        if until:
            until_dt = datetime.fromisoformat(until)
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)
            end_time = int(until_dt.timestamp())

        return await self._collector.trigger(start_time=start_time, end_time=end_time)


class ListCVEs:
    """
    List CVEs from cve-core within a date range.

    Converts human-friendly ISO date strings to timezone-aware datetimes
    and delegates to CVEStorePort.
    """

    def __init__(self, store: CVEStorePort) -> None:
        self._store = store

    async def execute(self, since: str, until: str | None = None) -> list[CVEInfo]:
        """
        Args:
            since: ISO 8601 date/datetime string for the lower bound, e.g. "2024-01-01".
            until: ISO 8601 date/datetime string for the upper bound, or None (no limit).

        Returns:
            List of CVEInfo ordered by date_updated DESC.
        """
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)

        until_dt = None
        if until:
            until_dt = datetime.fromisoformat(until)
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)

        return await self._store.list(start_time=since_dt, end_time=until_dt)


class ManageSchedule:
    """
    Create, list, and delete recurring CVE collection schedules via Temporal.
    """

    def __init__(self, scheduler: SchedulerPort) -> None:
        self._scheduler = scheduler

    async def create(self, schedule_id: str, cron: str, lookback_days: int) -> None:
        """Create a recurring schedule in Temporal."""
        await self._scheduler.create(
            schedule_id=schedule_id,
            cron=cron,
            lookback_days=lookback_days,
        )

    async def list(self) -> list[ScheduleInfo]:
        """Return all existing Temporal Schedules."""
        return await self._scheduler.list()

    async def delete(self, schedule_id: str) -> None:
        """Delete a Temporal Schedule by ID."""
        await self._scheduler.delete(schedule_id=schedule_id)
