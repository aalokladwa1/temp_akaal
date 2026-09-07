"""
akaalEngine.fabric
==================
P7B Group 1 -- Environment, Trust & Hybrid Connectivity Fabric.

This package is the distributed infrastructure/fabric plane that surrounds canonical
AKAAL execution (migration planning, ExecutionPlan, transport, CDC, checkpoints,
validation, security/authorization, telemetry, Evidence #12). It does not replace,
duplicate, or re-implement any of those authorities.

Conceptual data flow (see progress.md P7B Group-1 authorization for the full contract):

    PHYSICAL / CLOUD RESOURCE
        -> environment            (P7B.1  akaalEngine.fabric.environment)
        -> resource_identity       (P7B.2  akaalEngine.fabric.resource_identity)
        -> workload_identity       (P7B.3  akaalEngine.fabric.workload_identity)
        -> secrets_integration     (P7B.4  akaalEngine.fabric.secrets_integration)
        -> execution_site          (P7B.5  akaalEngine.fabric.execution_site)
        -> connectivity            (P7B.6/7 akaalEngine.fabric.connectivity)
        -> reachability            (P7B.8  akaalEngine.fabric.reachability)
        -> remote_execution        (P7B.9  akaalEngine.fabric.remote_execution)
        -> route_planning          (P7B.10 akaalEngine.fabric.route_planning)
        -> existing canonical AKAAL authorities (Engine/Pipeline) -> physical provider

Absolute invariants enforced across every submodule (never re-derive locally -- import
and reuse):
    * A locator (environment id / resource id / site id) is never itself authorization.
    * Cloud-native authentication is never itself AKAAL authorization
      (see akaalPipeline.security.central_authorization for the actual authorization
      authority; this package never grants AKAAL permissions on its own).
    * "Configured" is never "proven": private endpoint configuration, registered sites,
      and declared routes carry an explicit, separate proof/trust state that starts
      UNKNOWN/UNPROVEN and is only elevated by an actual probe or verified attestation.
"""
