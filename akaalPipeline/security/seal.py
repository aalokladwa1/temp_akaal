"""akaalPipeline.security.seal
============================
Canonical Execution Seal Builder.
Computes deterministic 14-dimension execution identity seal and SHA-256 fingerprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from akaalPipeline.contracts.serialization import canonical_fingerprint, canonical_serialize


@dataclass(frozen=True)
class ExecutionSeal:
    """Immutable 14-dimension execution identity seal."""

    seal_version: str
    tenant_id: str
    workspace_id: str
    project_id: str
    migration_id: str
    plan_id: str
    plan_revision: int
    execution_mode: str
    source_identity_fp: str
    target_identity_fp: str
    selection_scope_fp: str
    config_fp: str
    initialization_fp: str
    approval_fp: str
    fence_epoch: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seal_version": self.seal_version,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "migration_id": self.migration_id,
            "plan_id": self.plan_id,
            "plan_revision": self.plan_revision,
            "execution_mode": self.execution_mode,
            "source_identity_fp": self.source_identity_fp,
            "target_identity_fp": self.target_identity_fp,
            "selection_scope_fp": self.selection_scope_fp,
            "config_fp": self.config_fp,
            "initialization_fp": self.initialization_fp,
            "approval_fp": self.approval_fp,
            "fence_epoch": self.fence_epoch,
        }

    @property
    def seal_fingerprint(self) -> str:
        """Deterministic SHA-256 fingerprint of seal per AKAAL_CANONICAL_PROFILE_V1."""
        return canonical_fingerprint(self.to_dict())


class ExecutionSealBuilder:
    """Builder for constructing ExecutionSeal instances."""

    SEAL_VERSION = "1.0.0"

    @classmethod
    def build_seal(
        cls,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        migration_id: str,
        plan_id: str,
        plan_revision: int,
        execution_mode: str,
        source_identity_fp: str = "",
        target_identity_fp: str = "",
        selection_scope_fp: str = "",
        config_fp: str = "",
        initialization_fp: str = "",
        approval_fp: str = "",
        fence_epoch: int = 1,
        **kwargs: Any,
    ) -> ExecutionSeal:
        src = source_identity_fp or kwargs.get("source_identity_fingerprint", "")
        tgt = target_identity_fp or kwargs.get("target_identity_fingerprint", "")
        sel = selection_scope_fp or kwargs.get("selection_scope_fingerprint", "")
        cfg = config_fp or kwargs.get("config_fingerprint", "")
        init = initialization_fp or kwargs.get("initialization_fingerprint", "")
        appr = approval_fp or kwargs.get("approval_fingerprint", "")
        f_epoch = fence_epoch if fence_epoch is not None else kwargs.get("fence_epoch", 1)

        return ExecutionSeal(
            seal_version=cls.SEAL_VERSION,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            migration_id=migration_id,
            plan_id=plan_id,
            plan_revision=plan_revision,
            execution_mode=execution_mode,
            source_identity_fp=src,
            target_identity_fp=tgt,
            selection_scope_fp=sel,
            config_fp=cfg,
            initialization_fp=init,
            approval_fp=appr,
            fence_epoch=f_epoch,
        )
