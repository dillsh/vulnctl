"""
GrpcCVEStoreAdapter — implements CVEStorePort via cve-core's gRPC API.

Calls CVEServiceServicer.ListCVEs and returns a list of CVEInfo.
"""

from datetime import datetime, timezone
from typing import Optional

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from src.contracts.gRPC.compiled.cve.v1.message_pb2 import ListCVEsRequest
from src.contracts.gRPC.compiled.cve.v1.service_pb2_grpc import CVEServiceServicerStub
from src.core.ports import CVEInfo


class GrpcCVEStoreAdapter:
    """CVEStorePort implementation that queries cve-core over gRPC."""

    def __init__(self, address: str) -> None:
        """
        Args:
            address: cve-core gRPC address, e.g. "localhost:50051".
        """
        self._address = address

    async def list(
        self,
        start_time: datetime,
        end_time: Optional[datetime],
    ) -> list[CVEInfo]:
        """
        Send ListCVEs request to cve-core.

        Args:
            start_time: Fetch CVEs with date_updated >= this datetime.
            end_time:   Fetch CVEs with date_updated <= this datetime, or None for no upper bound.

        Returns:
            List of CVEInfo ordered by date_updated DESC.
        """
        start_ts = Timestamp()
        start_ts.FromDatetime(start_time)

        request_kwargs: dict = {"start_time": start_ts}
        if end_time is not None:
            end_ts = Timestamp()
            end_ts.FromDatetime(end_time)
            request_kwargs["end_time"] = end_ts

        request = ListCVEsRequest(**request_kwargs)

        async with grpc.aio.insecure_channel(self._address) as channel:
            stub = CVEServiceServicerStub(channel)
            response = await stub.ListCVEs(request)

        return [
            CVEInfo(
                cve_id=cve.cve_id,
                status=cve.status,
                title=cve.title,
                vendor=cve.vendor,
                product=cve.product,
                date_updated=(
                    cve.date_updated.ToDatetime(tzinfo=timezone.utc)
                    if cve.HasField("date_updated") else None
                ),
            )
            for cve in response.cves
        ]
