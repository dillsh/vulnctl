"""
Application use cases — pure business logic, no framework dependencies.
"""

from src.core.ports import RecentCVEStorePort, CVEInfo


class LastCVEs:
    """
    List CVEs from the last N days (1-3).

    Delegates to RecentCVEStorePort; the server computes since = now - days.
    """

    def __init__(self, store: RecentCVEStorePort) -> None:
        self._store = store

    async def execute(self, days: int) -> list[CVEInfo]:
        """
        Args:
            days: Number of days to look back (1-3).

        Returns:
            List of CVEInfo ordered by date_updated DESC.
        """
        return await self._store.list(days=days)
