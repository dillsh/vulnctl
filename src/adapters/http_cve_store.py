"""
HttpCVEStoreAdapter — implements CVEStorePort via cve-core's REST API.

Used by the standalone binary (user.py) — no gRPC dependency required.
"""

from datetime import datetime, timezone
from typing import Optional

import httpx

from src.core.ports import AffectedInfo, CVEInfo


class HttpCVEStoreAdapter:
    """CVEStorePort implementation that queries cve-core over HTTP."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    async def list(
        self,
        start_time: datetime,
        end_time: Optional[datetime],
    ) -> list[CVEInfo]:
        params: dict = {"since": start_time.date().isoformat()}
        if end_time is not None:
            params["until"] = end_time.date().isoformat()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self._base_url}/api/v1/cves", params=params)
            response.raise_for_status()

        return [
            CVEInfo(
                cve_id=item["cve_id"],
                status=item["status"],
                title=item.get("title"),
                affected=[
                    AffectedInfo(vendor=a["vendor"], product=a["product"])
                    for a in (item.get("affected") or [])
                ] or None,
                date_updated=(
                    datetime.fromisoformat(item["date_updated"]).replace(tzinfo=timezone.utc)
                    if item.get("date_updated")
                    else None
                ),
            )
            for item in response.json()
        ]
