"""
gRPC package initialization.
"""

from akaal.api.grpc.service import AkaalV1Servicer
from akaal.api.grpc.server import AkaalGrpcServer

__all__ = ["AkaalV1Servicer", "AkaalGrpcServer"]
