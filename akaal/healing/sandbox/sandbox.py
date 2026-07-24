"""RepairSandbox: Isolated environment for dry-run simulation execution."""

from typing import Any
from akaal.healing.sandbox.simulation import SimulationEngine, SimulationReport


class RepairSandbox:
    """Isolated environment executing repair plan simulations."""

    def __init__(self):
        self.simulation_engine = SimulationEngine()

    def run_dry_run(self, plan: Any) -> SimulationReport:
        """Execute dry-run repair preview in sandbox."""
        return self.simulation_engine.simulate(plan)
