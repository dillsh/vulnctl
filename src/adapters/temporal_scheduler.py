"""
TemporalSchedulerAdapter — implements SchedulerPort via Temporal Schedules API.

Creates / lists / deletes Temporal Schedules that periodically trigger
CVECollectorWorkflow or SyncCPEDictionaryWorkflow on the cve-collector task queue.
"""

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
)

from src.config import settings
from src.contracts.gRPC.cve.v1.message_pb2 import CollectCVEsRequest  # type: ignore[attr-defined]
from src.core.ports import ScheduleInfo


class TemporalSchedulerAdapter:
    """SchedulerPort implementation backed by Temporal Schedules."""

    def __init__(self, client: Client) -> None:
        self._client = client

    async def create(self, schedule_id: str, cron: str) -> None:
        """
        Create a Temporal Schedule that starts CVECollectorWorkflow on `cron`.

        Each triggered run receives an empty CollectCVEsRequest so that
        cve-collector's activity resolves the collection window via the
        checkpoint stored in cve-core (start_time=0 → read checkpoint).

        Args:
            schedule_id: Unique schedule name in Temporal.
            cron:        Standard cron expression (UTC), e.g. "0 6 * * *".
        """
        await self._client.create_schedule(
            id=schedule_id,
            schedule=Schedule(
                action=ScheduleActionStartWorkflow(
                    "CVECollectorWorkflow",
                    args=[CollectCVEsRequest()],
                    id=f"cve-collect-{schedule_id}",
                    task_queue=settings.collector_task_queue,
                ),
                spec=ScheduleSpec(cron_expressions=[cron]),
                policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
            ),
        )

    async def list(self) -> list[ScheduleInfo]:
        """Return a summary of all existing Temporal Schedules.

        list_schedules() returns ScheduleListDescription whose .info is a
        lightweight ScheduleListInfo — it does NOT include the full spec/cron.
        We call handle.describe() per entry to get the full ScheduleDescription
        with schedule.spec. Acceptable because the number of schedules is small.
        """
        result: list[ScheduleInfo] = []
        async for entry in await self._client.list_schedules():
            handle = self._client.get_schedule_handle(entry.id)
            description = await handle.describe()

            cron = ""
            spec = description.schedule.spec
            if spec and spec.cron_expressions:
                cron = spec.cron_expressions[0]

            next_run: str | None = None
            if entry.info and entry.info.next_action_times:
                next_run = entry.info.next_action_times[0].isoformat()

            result.append(
                ScheduleInfo(
                    schedule_id=entry.id,
                    cron=cron,
                    next_run=next_run,
                )
            )
        return result

    async def create_cpe_sync(self, schedule_id: str, cron: str) -> None:
        """
        Create a Temporal Schedule that starts SyncCPEDictionaryWorkflow on `cron`.

        The workflow takes no arguments — it resolves the sync window itself
        via the "nvd-cpe" checkpoint stored in cve-core.
        """
        await self._client.create_schedule(
            id=schedule_id,
            schedule=Schedule(
                action=ScheduleActionStartWorkflow(
                    "SyncCPEDictionaryWorkflow",
                    id=f"sync-cpe-{schedule_id}",
                    task_queue=settings.collector_task_queue,
                ),
                spec=ScheduleSpec(cron_expressions=[cron]),
                policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
            ),
        )

    async def delete(self, schedule_id: str) -> None:
        """Delete a Temporal Schedule by name."""
        handle = self._client.get_schedule_handle(schedule_id)
        await handle.delete()
