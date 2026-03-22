"""
GrpcCollectorAdapter — implements CollectorPort via cve-collector's gRPC API.

Calls CVECollectorServicer.CollectCVEs and returns the workflow_id.
"""

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from src.contracts.gRPC.cve.v1.message_pb2 import CollectCVEsRequest
from src.contracts.gRPC.cve.v1.service_pb2_grpc import CVECollectorServicerStub
from src.core.ports import CollectionResult


class GrpcCollectorAdapter:
    """CollectorPort implementation that calls cve-collector over gRPC."""

    def __init__(self, address: str, api_key: str = "") -> None:
        """
        Args:
            address: cve-collector gRPC address, e.g. "localhost:50052".
            api_key: API key sent as x-api-key metadata.
        """
        self._address = address
        self._api_key = api_key

    async def trigger(self, start_time: int, end_time: int) -> CollectionResult:
        """
        Send CollectCVEs request to cve-collector.

        Args:
            start_time: Unix timestamp for collection window start.
            end_time:   Unix timestamp for collection window end (0 = not set).

        Returns:
            CollectionResult with the started Temporal workflow_id.
        """
        request_kwargs: dict = {"start_time": Timestamp(seconds=start_time)}
        if end_time:
            request_kwargs["end_time"] = Timestamp(seconds=end_time)

        request = CollectCVEsRequest(**request_kwargs)

        async with grpc.aio.insecure_channel(self._address) as channel:
            stub = CVECollectorServicerStub(channel)
            response = await stub.CollectCVEs(
                request, metadata=[("x-api-key", self._api_key)]
            )

        return CollectionResult(workflow_id=response.workflow_id)
