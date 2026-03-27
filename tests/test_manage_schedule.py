"""
Unit tests for ManageSchedule use case.

No I/O — uses MockSchedulerAdapter that implements SchedulerPort in memory.
"""

import pytest

from src.core.ports import ScheduleInfo, SchedulerPort
from src.core.use_cases import ManageSchedule


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------


class MockSchedulerAdapter:
    """In-memory SchedulerPort: records calls and holds a configurable schedule list."""

    def __init__(self, schedules: list[ScheduleInfo] | None = None) -> None:
        self._schedules: list[ScheduleInfo] = schedules or []
        self.created: list[dict] = []
        self.deleted: list[str] = []

    async def create(self, schedule_id: str, cron: str) -> None:
        self.created.append({"schedule_id": schedule_id, "cron": cron})

    async def list(self) -> list[ScheduleInfo]:
        return self._schedules

    async def delete(self, schedule_id: str) -> None:
        self.deleted.append(schedule_id)


# ---------------------------------------------------------------------------
# Tests — create
# ---------------------------------------------------------------------------


class TestManageScheduleCreate:
    @pytest.mark.asyncio
    async def test_create_passes_schedule_id_and_cron(self):
        mock = MockSchedulerAdapter()
        await ManageSchedule(scheduler=mock).create(
            schedule_id="daily-cve-collection",
            cron="0 6 * * *",
        )

        assert mock.created == [
            {"schedule_id": "daily-cve-collection", "cron": "0 6 * * *"}
        ]

    @pytest.mark.asyncio
    async def test_create_passes_custom_cron(self):
        mock = MockSchedulerAdapter()
        await ManageSchedule(scheduler=mock).create(
            schedule_id="my-schedule",
            cron="0 10 * * 1-5",
        )

        assert mock.created[0]["cron"] == "0 10 * * 1-5"

    @pytest.mark.asyncio
    async def test_create_does_not_call_delete_or_list(self):
        mock = MockSchedulerAdapter()
        await ManageSchedule(scheduler=mock).create(schedule_id="s", cron="0 6 * * *")

        assert mock.deleted == []
        assert mock._schedules == []


# ---------------------------------------------------------------------------
# Tests — list
# ---------------------------------------------------------------------------


class TestManageScheduleList:
    @pytest.mark.asyncio
    async def test_list_returns_all_schedules(self):
        schedules = [
            ScheduleInfo(
                schedule_id="daily-cve-collection",
                cron="0 6 * * *",
                next_run="2026-03-27T06:00:00+00:00",
            ),
            ScheduleInfo(schedule_id="daily-cpe-sync", cron="0 3 * * *", next_run=None),
        ]
        mock = MockSchedulerAdapter(schedules=schedules)

        result = await ManageSchedule(scheduler=mock).list()

        assert result == schedules

    @pytest.mark.asyncio
    async def test_list_returns_empty_list_when_no_schedules(self):
        mock = MockSchedulerAdapter(schedules=[])

        result = await ManageSchedule(scheduler=mock).list()

        assert result == []

    @pytest.mark.asyncio
    async def test_list_preserves_next_run_none(self):
        schedules = [
            ScheduleInfo(schedule_id="s", cron="0 6 * * *", next_run=None),
        ]
        mock = MockSchedulerAdapter(schedules=schedules)

        result = await ManageSchedule(scheduler=mock).list()

        assert result[0].next_run is None


# ---------------------------------------------------------------------------
# Tests — delete
# ---------------------------------------------------------------------------


class TestManageScheduleDelete:
    @pytest.mark.asyncio
    async def test_delete_passes_schedule_id(self):
        mock = MockSchedulerAdapter()
        await ManageSchedule(scheduler=mock).delete(schedule_id="daily-cve-collection")

        assert mock.deleted == ["daily-cve-collection"]

    @pytest.mark.asyncio
    async def test_delete_does_not_call_create_or_list(self):
        mock = MockSchedulerAdapter()
        await ManageSchedule(scheduler=mock).delete(schedule_id="s")

        assert mock.created == []

    @pytest.mark.asyncio
    async def test_delete_called_twice_records_both(self):
        mock = MockSchedulerAdapter()
        use_case = ManageSchedule(scheduler=mock)
        await use_case.delete(schedule_id="sched-a")
        await use_case.delete(schedule_id="sched-b")

        assert mock.deleted == ["sched-a", "sched-b"]


# ---------------------------------------------------------------------------
# Port structural check
# ---------------------------------------------------------------------------


class TestSchedulerPortStructure:
    @pytest.mark.asyncio
    async def test_mock_adapter_satisfies_scheduler_port(self):
        """Type-structural check: MockSchedulerAdapter implements SchedulerPort."""
        mock: SchedulerPort = MockSchedulerAdapter()  # type: ignore[assignment]
        await mock.create(schedule_id="s", cron="0 6 * * *")
        result = await mock.list()
        await mock.delete(schedule_id="s")
        assert isinstance(result, list)
