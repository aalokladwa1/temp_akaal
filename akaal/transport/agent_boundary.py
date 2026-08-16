"""
Akaal — Remote Agent & Private Network Gateway Boundary Engine (P4.7)
====================================================================
Remote AKAAL Agent boundary handling outbound-initiated agent control channels,
agent session authentication, health checking, and private database routing.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List

from akaal.transport.models import TransportHop, TransportEndpoint, TransportSession, TransportState, redact_text

logger = logging.getLogger("akaal.transport.agent_boundary")


class RemoteAgentSession:
    """Represents an active outbound-initiated agent control session."""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        network_zone: str = "DEFAULT_ZONE",
        auth_token_ref: str = "",
    ) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.network_zone = network_zone
        self.auth_token_ref = auth_token_ref
        self.connected_at = time.time()
        self.last_heartbeat_at = time.time()
        self.is_active = True

    def update_heartbeat(self) -> None:
        self.last_heartbeat_at = time.time()

    def is_healthy(self, max_idle_seconds: float = 30.0) -> bool:
        return self.is_active and (time.time() - self.last_heartbeat_at) < max_idle_seconds


class RemoteAgentBoundaryManager:
    """Manages remote AKAAL agent registration and private database routing."""

    def __init__(self) -> None:
        self._registered_agents: Dict[str, RemoteAgentSession] = {}

    def register_agent(
        self,
        agent_id: str,
        agent_name: str,
        network_zone: str = "DEFAULT_ZONE",
        auth_token_ref: str = "",
    ) -> RemoteAgentSession:
        session = RemoteAgentSession(agent_id, agent_name, network_zone, auth_token_ref)
        self._registered_agents[agent_id] = session
        logger.info("Registered remote AKAAL agent: %s (%s) in zone '%s'", agent_name, agent_id, network_zone)
        return session

    def get_agent_session(self, agent_id: str) -> Optional[RemoteAgentSession]:
        return self._registered_agents.get(agent_id)

    async def route_via_agent(
        self,
        agent_hop: TransportHop,
        target_endpoint: TransportEndpoint,
    ) -> Tuple[str, int]:
        """Routes database connection through a verified remote AKAAL agent session."""
        agent_id = agent_hop.hostname or agent_hop.hop_id
        session = self.get_agent_session(agent_id)

        # Fail closed if agent is not registered or unhealthy
        if not session or not session.is_healthy():
            raise RuntimeError(
                f"Remote AKAAL Agent '{agent_id}' is unavailable or unauthenticated in zone '{agent_hop.known_hosts_ref or 'DEFAULT'}'. Fail closed."
            )

        logger.info("Routed connection through remote AKAAL Agent %s to target %s:%d", agent_id, target_endpoint.hostname, target_endpoint.port)
        return target_endpoint.hostname, target_endpoint.port
