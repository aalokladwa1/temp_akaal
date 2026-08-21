"""akaalPipeline.state.aggregates
================================
MigrationAggregate root domain aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from akaalPipeline.contracts.enums import MigrationLifecycleState, MigrationMode
from akaalPipeline.contracts.errors import RevisionConflictError
from akaalPipeline.identity.lineage import LineageRecord
from akaalPipeline.security.context import PipelineActorContext
from akaalPipeline.state.lifecycle import MigrationLifecycleMachine


from akaalPipeline.configuration.invalidation import ConfigurationInvalidator


@dataclass
class MigrationAggregate:
    migration_id: str
    revision: int
    name: str
    mode: MigrationMode
    state: MigrationLifecycleState
    tenant_id: Optional[str] = None
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    configuration: Mapping[str, Any] = field(default_factory=dict)
    plan_id: Optional[str] = None
    initialization_id: Optional[str] = None
    active_attempt_id: Optional[str] = None
    active_schedule_id: Optional[str] = None
    lineage: LineageRecord = field(default_factory=lambda: LineageRecord.root())
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update_state(self, new_state: MigrationLifecycleState, expected_revision: int) -> None:
        if self.revision != expected_revision:
            raise RevisionConflictError(
                f"Revision conflict updating state of migration {self.migration_id!r}",
                expected_revision=expected_revision,
                actual_revision=self.revision,
            )
        MigrationLifecycleMachine.validate_transition(self.state, new_state)
        self.state = new_state
        self.revision += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def update_configuration(self, new_config: Mapping[str, Any], expected_revision: int) -> None:
        if self.revision != expected_revision:
            raise RevisionConflictError(
                f"Revision conflict updating configuration of migration {self.migration_id!r}",
                expected_revision=expected_revision,
                actual_revision=self.revision,
            )
        effect = ConfigurationInvalidator.classify_change(self.configuration, new_config)
        self.configuration = dict(new_config)
        if effect.invalidates_initialization or effect.invalidates_plan:
            self.initialization_id = None
            self.plan_id = None
            self.active_schedule_id = None
            self.state = MigrationLifecycleState.CONFIGURING
        elif self.state in (MigrationLifecycleState.DRAFT, MigrationLifecycleState.DISCOVERED, MigrationLifecycleState.PLANNED):
            self.state = MigrationLifecycleState.CONFIGURING
        self.revision += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_plan(self, plan_id: str, expected_revision: int) -> None:
        if self.revision != expected_revision:
            raise RevisionConflictError(
                f"Revision conflict setting plan for migration {self.migration_id!r}",
                expected_revision=expected_revision,
                actual_revision=self.revision,
            )
        self.plan_id = plan_id
        MigrationLifecycleMachine.validate_transition(self.state, MigrationLifecycleState.PLANNED)
        self.state = MigrationLifecycleState.PLANNED
        self.revision += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def set_initialization(self, initialization_id: str, expected_revision: int) -> None:
        if self.revision != expected_revision:
            raise RevisionConflictError(
                f"Revision conflict setting initialization for migration {self.migration_id!r}",
                expected_revision=expected_revision,
                actual_revision=self.revision,
            )
        self.initialization_id = initialization_id
        MigrationLifecycleMachine.validate_transition(self.state, MigrationLifecycleState.INITIALIZED)
        self.state = MigrationLifecycleState.INITIALIZED
        self.revision += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "migration_id": self.migration_id,
            "revision": self.revision,
            "name": self.name,
            "mode": self.mode.value,
            "state": self.state.value,
            "tenant_id": self.tenant_id,
            "workspace_id": self.workspace_id,
            "project_id": self.project_id,
            "configuration": dict(self.configuration),
            "plan_id": self.plan_id,
            "initialization_id": self.initialization_id,
            "active_attempt_id": self.active_attempt_id,
            "active_schedule_id": self.active_schedule_id,
            "lineage": self.lineage.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MigrationAggregate:
        return cls(
            migration_id=data["migration_id"],
            revision=data["revision"],
            name=data["name"],
            mode=MigrationMode(data["mode"]),
            state=MigrationLifecycleState(data["state"]),
            tenant_id=data.get("tenant_id"),
            workspace_id=data.get("workspace_id"),
            project_id=data.get("project_id"),
            configuration=data.get("configuration", {}),
            plan_id=data.get("plan_id"),
            initialization_id=data.get("initialization_id"),
            active_attempt_id=data.get("active_attempt_id"),
            active_schedule_id=data.get("active_schedule_id"),
            lineage=LineageRecord.from_dict(data["lineage"]),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )
