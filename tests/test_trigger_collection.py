"""
Unit tests for TriggerCollection use case.

No I/O — uses MockCollectorAdapter that implements CollectorPort in memory.
"""

import pytest

from src.core.ports import CollectionResult, CollectorPort
from src.core.use_cases import TriggerCollection


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------


class MockCollectorAdapter:
    """In-memory CollectorPort: captures args and returns a fixed workflow_id."""

    def __init__(self, workflow_id: str = "mock-wf-123") -> None:
        self.workflow_id = workflow_id
        self.captured_start_time: int = -1
        self.captured_end_time: int = -1

    async def trigger(self, start_time: int, end_time: int) -> CollectionResult:
        self.captured_start_time = start_time
        self.captured_end_time = end_time
        return CollectionResult(workflow_id=self.workflow_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTriggerCollection:
    @pytest.mark.asyncio
    async def test_returns_workflow_id(self):
        mock = MockCollectorAdapter(workflow_id="wf-abc")
        result = await TriggerCollection(collector=mock).execute(
            since="2024-01-01", until=None
        )
        assert result.workflow_id == "wf-abc"

    @pytest.mark.asyncio
    async def test_since_converted_to_epoch(self):
        mock = MockCollectorAdapter()
        await TriggerCollection(collector=mock).execute(since="2024-01-01", until=None)

        # 2024-01-01 00:00:00 UTC = 1704067200
        assert mock.captured_start_time == 1704067200

    @pytest.mark.asyncio
    async def test_until_none_passes_zero_end_time(self):
        mock = MockCollectorAdapter()
        await TriggerCollection(collector=mock).execute(since="2024-01-01", until=None)

        assert mock.captured_end_time == 0

    @pytest.mark.asyncio
    async def test_until_converted_to_epoch(self):
        mock = MockCollectorAdapter()
        await TriggerCollection(collector=mock).execute(
            since="2024-01-01", until="2024-01-31"
        )

        # 2024-01-31 00:00:00 UTC = 1706659200
        assert mock.captured_end_time == 1706659200

    @pytest.mark.asyncio
    async def test_end_time_greater_than_start_time(self):
        mock = MockCollectorAdapter()
        await TriggerCollection(collector=mock).execute(
            since="2024-01-01", until="2024-01-31"
        )

        assert mock.captured_end_time > mock.captured_start_time

    @pytest.mark.asyncio
    async def test_mock_adapter_satisfies_collector_port(self):
        """Type-structural check: MockCollectorAdapter implements CollectorPort."""
        mock: CollectorPort = MockCollectorAdapter()  # type: ignore[assignment]
        result = await mock.trigger(start_time=1000, end_time=2000)
        assert isinstance(result, CollectionResult)
