"""
Unit tests for ListCVEs use case.

No I/O — uses MockCVEStoreAdapter that implements CVEStorePort in memory.
"""

from datetime import datetime, timezone
from typing import Optional

import pytest

from src.core.ports import AffectedInfo, CVEInfo, CVEStorePort
from src.core.use_cases import ListCVEs


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_cve(cve_id: str = "CVE-2024-0001") -> CVEInfo:
    return CVEInfo(
        cve_id=cve_id,
        status="PUBLISHED",
        title="Test vulnerability",
        affected=[AffectedInfo(vendor="test-vendor", product="test-product")],
        date_updated=datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------

class MockCVEStoreAdapter:
    """In-memory CVEStorePort: captures args and returns a configurable list."""

    def __init__(self, results: list[CVEInfo] | None = None) -> None:
        self.results: list[CVEInfo] = results or []
        self.captured_start_time: Optional[datetime] = None
        self.captured_end_time: Optional[datetime] = None

    async def list(
        self,
        start_time: datetime,
        end_time: Optional[datetime],
    ) -> list[CVEInfo]:
        self.captured_start_time = start_time
        self.captured_end_time = end_time
        return self.results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestListCVEs:

    @pytest.mark.asyncio
    async def test_since_converted_to_utc_datetime(self):
        mock = MockCVEStoreAdapter()
        await ListCVEs(store=mock).execute(since="2024-01-01")

        assert mock.captured_start_time == datetime(2024, 1, 1, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_until_none_passes_none_end_time(self):
        mock = MockCVEStoreAdapter()
        await ListCVEs(store=mock).execute(since="2024-01-01", until=None)

        assert mock.captured_end_time is None

    @pytest.mark.asyncio
    async def test_until_converted_to_utc_datetime(self):
        mock = MockCVEStoreAdapter()
        await ListCVEs(store=mock).execute(since="2024-01-01", until="2024-06-30")

        assert mock.captured_end_time == datetime(2024, 6, 30, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_end_time_greater_than_start_time(self):
        mock = MockCVEStoreAdapter()
        await ListCVEs(store=mock).execute(since="2024-01-01", until="2024-06-30")

        assert mock.captured_end_time > mock.captured_start_time

    @pytest.mark.asyncio
    async def test_returns_cve_list_from_store(self):
        cves = [_make_cve("CVE-2024-0001"), _make_cve("CVE-2024-0002")]
        mock = MockCVEStoreAdapter(results=cves)

        result = await ListCVEs(store=mock).execute(since="2024-01-01")

        assert result == cves

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_store_has_no_results(self):
        mock = MockCVEStoreAdapter(results=[])

        result = await ListCVEs(store=mock).execute(since="2024-01-01")

        assert result == []

    @pytest.mark.asyncio
    async def test_naive_since_datetime_gets_utc_tzinfo(self):
        """ISO strings without timezone offset are treated as UTC."""
        mock = MockCVEStoreAdapter()
        await ListCVEs(store=mock).execute(since="2024-06-15T10:30:00")

        assert mock.captured_start_time.tzinfo == timezone.utc
        assert mock.captured_start_time == datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_naive_until_datetime_gets_utc_tzinfo(self):
        """ISO strings without timezone offset are treated as UTC."""
        mock = MockCVEStoreAdapter()
        await ListCVEs(store=mock).execute(since="2024-01-01", until="2024-12-31T23:59:59")

        assert mock.captured_end_time.tzinfo == timezone.utc
        assert mock.captured_end_time == datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_mock_adapter_satisfies_cve_store_port(self):
        """Type-structural check: MockCVEStoreAdapter implements CVEStorePort."""
        mock: CVEStorePort = MockCVEStoreAdapter()  # type: ignore[assignment]
        result = await mock.list(
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=None,
        )
        assert result == []
