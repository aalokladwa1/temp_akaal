"""
akaalEngine.fabric.remote_execution.control_plane
====================================================
P7B.9 -- Control-plane issuance of RemoteExecutionAssignments.

Delegates every trust/tenant/fencing decision to
akaalEngine.fabric.execution_site.SiteRegistry.assign_execution -- this module contains
NO independent trust, tenant-binding, or fencing logic of its own. Its only added
responsibility is producing the signed, time-bounded, transport-safe
RemoteExecutionAssignment object once SiteRegistry has already said yes.

Control plane vs execution/data plane (P7B Group-1 §9):
    * Control plane (this module): coordinates intent, plan identity, site assignment.
    * Execution/data plane (the remote site's canonical AKAAL runtime, NOT built here):
      performs the actual authorized connection/read/transfer/write/checkpoint/CDC/
      validation/telemetry/Evidence emission using the EXISTING canonical Engine
      authorities -- this control plane does not invent a second runtime, transport
      authority, checkpoint engine, or retry engine to do that work.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from akaalEngine.fabric.execution_site.registry import SiteAuthorizationCallback, SiteRegistry
from akaalEngine.fabric.execution_site.models import SiteAssignment
from akaalEngine.fabric.remote_execution.models import (
    AssignmentSigner,
    HMACAssignmentSigner,
    RemoteExecutionAssignment,
    RemoteExecutionError,
    _canonical_payload,
)


class RemoteExecutionControlPlane:
    def __init__(self, site_registry: SiteRegistry) -> None:
        self.site_registry = site_registry

    def issue_assignment(
        self,
        *,
        site_id: str,
        tenant_id: str,
        workspace_id: str,
        project_id: str,
        migration_id: str,
        plan_id: str,
        plan_revision: int,
        execution_identity_seal_fingerprint: str,
        fencing_epoch: int,
        correlation_id: str,
        authorization_callback: Optional[SiteAuthorizationCallback],
        signing_key: Optional[bytes] = None,
        signer: Optional[AssignmentSigner] = None,
        ttl_minutes: float = 15.0,
    ) -> RemoteExecutionAssignment:
        """
        Exactly one of `signing_key` (default symmetric HMAC, dev/test-friendly) or
        `signer` (production KMS/asymmetric-signing-ready AssignmentSigner) must be
        supplied -- there is no built-in default key. See the architecture note in
        akaalEngine.fabric.remote_execution.models for why this control plane never owns
        or generates key material itself.
        """
        if bool(signing_key) == bool(signer):
            raise RemoteExecutionError("issue_assignment requires exactly one of signing_key or signer.")
        active_signer: AssignmentSigner = signer or HMACAssignmentSigner(signing_key)
        if not execution_identity_seal_fingerprint:
            raise RemoteExecutionError("issue_assignment requires a non-empty execution_identity_seal_fingerprint.")

        # The ONLY trust/tenant/fencing decision point -- reused, never duplicated.
        site_assignment = SiteAssignment(
            site_id=site_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            migration_id=migration_id,
            plan_id=plan_id,
            fencing_epoch=fencing_epoch,
        )
        self.site_registry.assign_execution(site_assignment, authorization_callback=authorization_callback)

        assignment_id = f"assign-{uuid.uuid4().hex[:16]}"
        issued_at = datetime.now(timezone.utc).isoformat()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()

        payload = _canonical_payload(
            assignment_id, site_id, tenant_id, workspace_id, project_id, migration_id,
            plan_id, plan_revision, execution_identity_seal_fingerprint, fencing_epoch,
            correlation_id, issued_at, expires_at,
        )
        signature = active_signer.sign(payload)

        return RemoteExecutionAssignment(
            assignment_id=assignment_id,
            site_id=site_id,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            project_id=project_id,
            migration_id=migration_id,
            plan_id=plan_id,
            plan_revision=plan_revision,
            execution_identity_seal_fingerprint=execution_identity_seal_fingerprint,
            fencing_epoch=fencing_epoch,
            correlation_id=correlation_id,
            signature=signature,
            issued_at=issued_at,
            expires_at=expires_at,
        )
