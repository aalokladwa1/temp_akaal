"""ReplicationSandbox: Isolated environment for dry-run simulation execution."""

from typing import Any
from akaal.replication.sandbox.simulation import SimulationEngine, SimulationReport


class ReplicationSandbox:
    """Isolated environment executing replication plan simulations."""

    def __init__(self):
        self.simulation_engine = SimulationEngine()

    def run_dry_run(self, plan: Any) -> SimulationReport:
        """Execute dry-run replication preview in sandbox."""
        return self.simulation_engine.simulate(plan)
