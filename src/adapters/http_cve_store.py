"""
HttpCVEStoreAdapter — implements RecentCVEStorePort via cve-core's REST API.

Calls GET /api/v1/cves/last?days=N — no API key required.
Used by `cve last` (public user command).
"""

from datetime import datetime, timezone

import httpx

from src.core.ports import AffectedInfo, CVEInfo


class HttpCVEStoreAdapter:
    """RecentCVEStorePort implementation that queries cve-core over HTTP."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def list(self, days: int) -> list[CVEInfo]:
        """
        Fetch CVEs from the last N days via GET /api/v1/cves/last?days=N.

        Args:
            days: Number of days to look back (1–3). Validated server-side.

        Returns:
            List of CVEInfo ordered by date_updated DESC.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/cves/last",
                params={"days": days},
            )
            response.raise_for_status()

        return [
            CVEInfo(
                cve_id=item["cve_id"],
                status=item["status"],
                title=item.get("title"),
                affected=[
                    AffectedInfo(
                        vendor=a["vendor"],
                        product=a["product"],
                        version=a.get("version"),
                        cpe=a.get("cpe"),
                    )
                    for a in (item.get("affected") or [])
                ]
                or None,
                date_updated=(
                    datetime.fromisoformat(item["date_updated"]).replace(
                        tzinfo=timezone.utc
                    )
                    if item.get("date_updated")
                    else None
                ),
            )
            for item in response.json()
        ]
