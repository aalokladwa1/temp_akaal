"""akaalPipeline.capabilities.resolver
======================================
Multi-dimensional capability truth resolver.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from akaalPipeline.capabilities.bindings import BindingRegistry
from akaalPipeline.capabilities.catalog import CapabilityCatalog
from akaalPipeline.capabilities.dependencies import DependencyEvaluator
from akaalPipeline.contracts.enums import CapabilityDimension, MigrationMode


@dataclass(frozen=True)
class CapabilityEvaluationResult:
    capability_id: str
    is_available: bool
    blockers: List[str] = field(default_factory=list)
    dimension_status: Dict[CapabilityDimension, bool] = field(default_factory=dict)


class CapabilityResolver:
    def __init__(
        self,
        catalog: CapabilityCatalog,
        binding_registry: BindingRegistry,
    ) -> None:
        self.catalog = catalog
        self.binding_registry = binding_registry
        self.dependency_evaluator = DependencyEvaluator(catalog)

    def evaluate_capability(
        self,
        capability_id: str,
        mode: MigrationMode,
        *,
        active_binding_id: Optional[str] = None,
        is_authorized: bool = True,
        is_ready: bool = True,
    ) -> CapabilityEvaluationResult:
        blockers: List[str] = []
        dim_status: Dict[CapabilityDimension, bool] = {}

        # 1. CATALOG check
        desc = self.catalog.get(capability_id)
        if desc is None:
            blockers.append(f"Capability {capability_id!r} not found in catalog.")
            dim_status[CapabilityDimension.CATALOG] = False
            return CapabilityEvaluationResult(
                capability_id=capability_id,
                is_available=False,
                blockers=blockers,
                dimension_status=dim_status,
            )
        dim_status[CapabilityDimension.CATALOG] = True

        # 2. ELIGIBILITY check (mode support)
        if mode not in desc.supported_modes:
            blockers.append(f"Capability {capability_id!r} does not support mode {mode.value!r}.")
            dim_status[CapabilityDimension.ELIGIBILITY] = False
        else:
            dim_status[CapabilityDimension.ELIGIBILITY] = True

        # 3. BINDING check (truthful check for physical engine binding)
        all_bindings = self.binding_registry.list_all()
        if active_binding_id:
            binding = self.binding_registry.get(active_binding_id)
            bindings_to_check = [binding] if binding else []
        else:
            bindings_to_check = all_bindings

        if not bindings_to_check:
            blockers.append(f"No physical engine binding registered for capability {capability_id!r} (UNBOUND).")
            dim_status[CapabilityDimension.BINDING] = False
            dim_status[CapabilityDimension.HEALTH] = False
        else:
            dim_status[CapabilityDimension.BINDING] = True
            healthy_bindings = [b for b in bindings_to_check if b and b.is_healthy]
            if not healthy_bindings:
                blockers.append(f"Registered engine binding for capability {capability_id!r} is unhealthy (UNAVAILABLE).")
                dim_status[CapabilityDimension.HEALTH] = False
            else:
                dim_status[CapabilityDimension.HEALTH] = True

        # 4. DEPENDENCY check
        deps_satisfied, missing_deps = self.dependency_evaluator.evaluate_dependencies([capability_id])
        if not deps_satisfied:
            blockers.append(f"Missing required dependencies: {sorted(missing_deps)}")
            dim_status[CapabilityDimension.DEPENDENCY] = False
        else:
            dim_status[CapabilityDimension.DEPENDENCY] = True

        # 5. POLICY / AUTHORIZATION check
        dim_status[CapabilityDimension.POLICY] = is_authorized
        if not is_authorized:
            blockers.append("Policy/authorization check failed (POLICY_DENIED).")

        # 6. READINESS check
        dim_status[CapabilityDimension.READINESS] = is_ready
        if not is_ready:
            blockers.append("Resource/readiness check failed (NOT_READY).")

        is_available = len(blockers) == 0
        return CapabilityEvaluationResult(
            capability_id=capability_id,
            is_available=is_available,
            blockers=blockers,
            dimension_status=dim_status,
        )
