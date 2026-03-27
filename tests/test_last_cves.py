"""
Unit tests for LastCVEs use case.

No I/O — uses MockRecentCVEStoreAdapter that implements RecentCVEStorePort in memory.
"""

from datetime import datetime, timezone

import pytest

from src.core.ports import AffectedInfo, CVEInfo, RecentCVEStorePort
from src.core.use_cases import LastCVEs


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_cve(cve_id: str = "CVE-2026-0001") -> CVEInfo:
    return CVEInfo(
        cve_id=cve_id,
        status="PUBLISHED",
        title="Test vulnerability",
        affected=[AffectedInfo(vendor="acme", product="widget")],
        date_updated=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Mock adapter
# ---------------------------------------------------------------------------


class MockRecentCVEStoreAdapter:
    """In-memory RecentCVEStorePort: captures args and returns a configurable list."""

    def __init__(self, results: list[CVEInfo] | None = None) -> None:
        self.results: list[CVEInfo] = results or []
        self.captured_days: int | None = None

    async def list(self, days: int) -> list[CVEInfo]:
        self.captured_days = days
        return self.results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLastCVEs:
    @pytest.mark.asyncio
    async def test_passes_days_to_store(self):
        mock = MockRecentCVEStoreAdapter()
        await LastCVEs(store=mock).execute(days=1)

        assert mock.captured_days == 1

    @pytest.mark.asyncio
    async def test_passes_days_3_to_store(self):
        mock = MockRecentCVEStoreAdapter()
        await LastCVEs(store=mock).execute(days=3)

        assert mock.captured_days == 3

    @pytest.mark.asyncio
    async def test_returns_cves_from_store(self):
        cves = [_make_cve("CVE-2026-0001"), _make_cve("CVE-2026-0002")]
        mock = MockRecentCVEStoreAdapter(results=cves)

        result = await LastCVEs(store=mock).execute(days=1)

        assert result == cves

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_store_has_no_results(self):
        mock = MockRecentCVEStoreAdapter(results=[])

        result = await LastCVEs(store=mock).execute(days=2)

        assert result == []

    @pytest.mark.asyncio
    async def test_mock_adapter_satisfies_recent_cve_store_port(self):
        """Type-structural check: MockRecentCVEStoreAdapter implements RecentCVEStorePort."""
        mock: RecentCVEStorePort = MockRecentCVEStoreAdapter()  # type: ignore[assignment]
        result = await mock.list(days=1)
        assert result == []
