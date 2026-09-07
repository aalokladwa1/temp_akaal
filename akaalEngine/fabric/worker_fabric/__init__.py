"""
akaalEngine.fabric.worker_fabric
====================================
P7B.22 -- Elastic Worker Fabric (P7B Group 2, Campaign D).

Scope discipline: this package represents EXECUTION-CAPACITY workers that run migration
work at an akaalEngine.fabric.execution_site.ExecutionSite -- it is deliberately distinct
from, and never a duplicate of, two pre-existing "node"/"worker" concepts already in this
codebase:

  * `akaalPipeline.fleet.fleet_service.FleetOperationalService` -- AKAAL CONTROL-PLANE
    node operational management (liveness/drain of pipeline cluster nodes themselves),
    which explicitly delegates its own canonical node registry to
    `akaalEngine.runtime.distributed.coordinator`.
  * `akaalEngine.runtime.distributed.coordinator.LeaderElectionCoordinator` -- control-
    plane leader election/CAS coordination.

Neither of those is about elastic EXECUTION capacity for running migration workloads at a
Fabric execution site, which is this package's entire and only scope. This package does
not import, extend, or re-implement either of them.
"""
