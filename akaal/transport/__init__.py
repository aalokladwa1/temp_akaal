"""
AKAAL P4.7 — Universal Private / On-Prem / Hybrid Connectivity & Generalized Transport Runtime
=============================================================================================
Canonical enterprise transport package establishing, governing, diagnosing, and recovering
network connection paths across local, private, cloud, hybrid, bastion, proxy, and agent endpoints.
"""

from akaal.transport.models import (
    TransportMethod,
    TransportState,
    TransportFailureClass,
    TransportEndpoint,
    TransportHop,
    TransportPath,
    TransportSession,
    TransportDiagnostics,
)
from akaal.transport.transport_manager import TransportManager, get_global_transport_manager

__all__ = [
    "TransportMethod",
    "TransportState",
    "TransportFailureClass",
    "TransportEndpoint",
    "TransportHop",
    "TransportPath",
    "TransportSession",
    "TransportDiagnostics",
    "TransportManager",
    "get_global_transport_manager",
]
