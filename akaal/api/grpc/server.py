"""
gRPC Server Manager.
"""

from typing import Optional
from akaal.api.grpc.service import AkaalV1Servicer


class AkaalGrpcServer:
    """Enterprise gRPC Server Manager."""

    def __init__(self, port: int = 50051, servicer: Optional[AkaalV1Servicer] = None) -> None:
        self.port = port
        self.servicer = servicer or AkaalV1Servicer()
        self.is_running = False

    def start(self) -> None:
        """Start gRPC server instance."""
        self.is_running = True

    def stop(self) -> None:
        """Gracefully shutdown gRPC server instance."""
        self.is_running = False
