"""
akaalEngine.extensions.certification.profiles
=============================================
Data-driven certification profiles.
Builds certification profiles dynamically from provider capability declarations,
avoiding hard-coded provider taxonomies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from akaalEngine.extensions.certification.obligations import (
    CertificationObligation,
    ObligationCategory,
)

# Standard Universal Obligations (apply to all providers regardless of category)
UNIVERSAL_OBLIGATIONS = (
    CertificationObligation(
        obligation_id="OBL-ID-01",
        name="Manifest and Package Structure",
        category=ObligationCategory.IDENTITY_PACKAGING,
        description="Verifies manifest integrity, extension identity, and author provenance.",
        is_mandatory=True,
    ),
    CertificationObligation(
        obligation_id="OBL-SEC-01",
        name="Secret Isolation Conformance",
        category=ObligationCategory.CONNECTION_SECURITY,
        description="Ensures secrets are resolved exclusively through SecretConsumer without leakage.",
        is_mandatory=True,
    ),
    CertificationObligation(
        obligation_id="OBL-COMPAT-01",
        name="Engine Version Compatibility",
        category=ObligationCategory.COMPATIBILITY,
        description="Verifies the extension satisfies the host AKAAL engine compatibility range.",
        is_mandatory=True,
    ),
    CertificationObligation(
        obligation_id="OBL-FAIL-01",
        name="Failure Taxonomy Classification",
        category=ObligationCategory.FAILURE_HANDLING,
        description="Verifies errors conform to the canonical AKAAL error taxonomy without raw unhandled crashes.",
        is_mandatory=True,
    ),
)

# Capability-Triggered Obligations
CAPABILITY_OBLIGATIONS = (
    CertificationObligation(
        obligation_id="OBL-DISC-01",
        name="Schema Discovery Contract",
        category=ObligationCategory.DISCOVERY_SCHEMA,
        description="Verifies discovery strategy returns well-formed metadata objects conforming to SPI.",
        is_mandatory=True,
        trigger_capability="SCHEMA_DISCOVERY",
    ),
    CertificationObligation(
        obligation_id="OBL-TX-01",
        name="Transaction ACID Semantics",
        category=ObligationCategory.SEMANTICS,
        description="Verifies atomic commit and rollback behavior across transactional operations.",
        is_mandatory=True,
        trigger_capability="TRANSACTION_ACID",
    ),
    CertificationObligation(
        obligation_id="OBL-CDC-01",
        name="Change Data Capture Stream",
        category=ObligationCategory.DATA_MOVEMENT,
        description="Verifies CDC streaming events, ordering preservation, and schema propagation.",
        is_mandatory=True,
        trigger_capability="CDC_STREAM",
    ),
    CertificationObligation(
        obligation_id="OBL-CDC-CHECKPOINT-01",
        name="CDC Checkpoint and Restart",
        category=ObligationCategory.DURABILITY,
        description="Verifies that CDC stream state can be checkpointed and restarted deterministically.",
        is_mandatory=True,
        trigger_capability="CDC_STREAM",
    ),
    CertificationObligation(
        obligation_id="OBL-MSG-01",
        name="Message Delivery and Acknowledgment",
        category=ObligationCategory.SEMANTICS,
        description="Verifies message queue acknowledgment, rejection, and at-least-once semantics.",
        is_mandatory=True,
        trigger_capability="MESSAGING",
    ),
    CertificationObligation(
        obligation_id="OBL-BULK-READ-01",
        name="Bounded Bulk Read",
        category=ObligationCategory.DATA_MOVEMENT,
        description="Verifies streaming bulk read bounded memory limits.",
        is_mandatory=True,
        trigger_capability="BULK_READ",
    ),
    CertificationObligation(
        obligation_id="OBL-BULK-WRITE-01",
        name="Bounded Bulk Write",
        category=ObligationCategory.DATA_MOVEMENT,
        description="Verifies bulk write batching, constraint error handling, and backpressure.",
        is_mandatory=True,
        trigger_capability="BULK_WRITE",
    ),
)


@dataclass(frozen=True)
class CertificationProfile:
    """
    Data-driven suite of certification obligations.
    Composed dynamically from the capabilities a provider actually advertises.
    """
    name: str
    target_capabilities: frozenset[str]
    obligations: tuple[CertificationObligation, ...]

    @classmethod
    def from_capabilities(
        cls,
        capabilities: Sequence[str],
        name: str = "dynamic_profile",
    ) -> CertificationProfile:
        norm_caps = frozenset(c.strip().upper() for c in capabilities if c)
        applicable = list(UNIVERSAL_OBLIGATIONS)
        for obl in CAPABILITY_OBLIGATIONS:
            if obl.is_applicable(list(norm_caps)):
                applicable.append(obl)
        return cls(name=name, target_capabilities=norm_caps, obligations=tuple(applicable))


def build_profile_for_capabilities(capabilities: Sequence[str], name: str = "dynamic") -> CertificationProfile:
    return CertificationProfile.from_capabilities(capabilities, name=name)


# Predefined Standard Profiles (built purely from standard capability sets)
RELATIONAL_PROFILE = build_profile_for_capabilities(
    ["SCHEMA_DISCOVERY", "TRANSACTION_ACID", "BULK_READ", "BULK_WRITE"],
    name="Standard Relational Profile",
)

MESSAGING_PROFILE = build_profile_for_capabilities(
    ["MESSAGING", "BULK_READ", "BULK_WRITE"],
    name="Standard Messaging Profile",
)

STREAMING_PROFILE = build_profile_for_capabilities(
    ["CDC_STREAM", "BULK_READ"],
    name="Standard Streaming Profile",
)

NOSQL_PROFILE = build_profile_for_capabilities(
    ["SCHEMA_DISCOVERY", "BULK_READ", "BULK_WRITE"],
    name="Standard NoSQL Profile",
)

SAAS_PROFILE = build_profile_for_capabilities(
    ["SCHEMA_DISCOVERY", "BULK_READ"],
    name="Standard SaaS Profile",
)
