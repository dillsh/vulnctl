"""
GrpcCVEStoreAdapter — implements CVEStorePort via cve-core's gRPC API.

Calls CVEServiceServicer.ListCVEs and returns a list of CVEInfo.
"""

from datetime import datetime, timezone
from typing import Optional

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from src.contracts.gRPC.cve.v1.message_pb2 import ListCVEsRequest  # type: ignore[attr-defined]
from src.contracts.gRPC.cve.v1.service_pb2_grpc import CVEServiceServicerStub
from src.core.ports import CVEInfo, AffectedInfo


class GrpcCVEStoreAdapter:
    """CVEStorePort implementation that queries cve-core over gRPC."""

    def __init__(self, address: str, api_key: str = "") -> None:
        """
        Args:
            address: cve-core gRPC address, e.g. "localhost:50051".
            api_key: API key sent as x-api-key metadata.
        """
        self._address = address
        self._api_key = api_key

    async def list(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[CVEInfo]:
        """
        Send ListCVEs request to cve-core.

        Args:
            start_time: Fetch CVEs with date_updated >= this datetime.
            end_time:   Fetch CVEs with date_updated <= this datetime, or None for no upper bound.

        Returns:
            List of CVEInfo ordered by date_updated DESC.
        """
        request_kwargs: dict = {}

        if start_time is not None:
            start_ts = Timestamp()
            start_ts.FromDatetime(start_time)
            request_kwargs["start_time"] = start_ts
        if end_time is not None:
            end_ts = Timestamp()
            end_ts.FromDatetime(end_time)
            request_kwargs["end_time"] = end_ts

        request = ListCVEsRequest(**request_kwargs)

        async with grpc.aio.insecure_channel(self._address) as channel:
            stub = CVEServiceServicerStub(channel)
            response = await stub.ListCVEs(
                request, metadata=[("x-api-key", self._api_key)]
            )
            return [
                CVEInfo(
                    cve_id=cve.cve_id,
                    status=cve.status,
                    title=cve.title or "",
                    affected=(
                        [
                            AffectedInfo(
                                vendor=a.vendor,
                                product=a.product,
                                version=a.version or None,
                                cpe=list(a.cpe) or None,
                            )
                            for a in cve.affected
                        ]
                        or None
                    ),
                    date_updated=(
                        cve.date_updated.ToDatetime(tzinfo=timezone.utc)
                        if cve.HasField("date_updated")
                        else None
                    ),
                )
                for cve in response.cves
            ]
