"""
Akaal — Encryption Configuration & Constraints Validator
=========================================================
Checks target database licensing limits, version restrictions, and KMS provider configurations.
"""

from typing import Any, Dict, List, Set, Optional

from akaal.core.models.enums import SystemType
from akaal.core.comparison.models import Schema
from akaal.core.intelligence.common.models import Diagnostic, Severity, DiagnosticCategory
from akaal.core.intelligence.encryption_aware.exceptions import EncryptionValidationError
from akaal.core.intelligence.encryption_aware.models import (
    EncryptionTranslation,
    EncryptionCompatibilityTier,
    EncryptionAlgorithm,
)

class EncryptionLayoutValidator:
    """Audits configurations to flag licensing boundaries and engine incompatibilities."""

    def validate_encryption(
        self,
        schema: Schema,
        translations: Dict[str, EncryptionTranslation],
        target_version: str,
        target_engine: str,
        target_edition: str,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> List[Diagnostic]:
        """Runs the validation rules suite, compiling structured diagnostics."""
        diagnostics = []

        # Parse target version elements
        v_parts = []
        for p in target_version.split("."):
            try:
                v_parts.append(int(p))
            except ValueError:
                pass

        for table in schema.tables:
            trans = translations.get(table.name)
            if not trans:
                continue

            # 1. Check SQL Server TDE Edition Limitations
            if trans.target_dialect == SystemType.MSSQL:
                # Before SQL Server 2019 (15.0), TDE was limited to ENTERPRISE or DEVELOPER editions
                is_pre_2019 = False
                if v_parts and v_parts[0] < 15:
                    is_pre_2019 = True

                if is_pre_2019 and target_edition.upper() == "STANDARD":
                    diagnostics.append(Diagnostic(
                        diagnostic_code="ENCRYPTION_EDITION_LIMITATION",
                        severity=Severity.CRITICAL,
                        category=DiagnosticCategory.COMPATIBILITY,
                        message=f"Table '{table.name}' uses TDE which is restricted to Enterprise/Developer editions on SQL Server versions prior to 2019.",
                        path=f"tables.{table.name}",
                        explanation="SQL Server Standard edition does not license Transparent Data Encryption (TDE) before Version 15.0.",
                        root_cause="SQL Server licensing matrix restrictions.",
                        suggested_fix="Upgrade target SQL Server engine to 2019 or above, or upgrade to Enterprise edition license.",
                        affected_event=table.name,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))

            # 2. Check unsupported algorithms (e.g. 3DES is deprecated and unsupported on MySQL/PostgreSQL native formats)
            if trans.target_algorithm == EncryptionAlgorithm.TRIPLE_DES:
                if trans.target_dialect in (SystemType.MYSQL, SystemType.POSTGRESQL):
                    diagnostics.append(Diagnostic(
                        diagnostic_code="ENCRYPTION_UNSUPPORTED_ALGORITHM",
                        severity=Severity.CRITICAL,
                        category=DiagnosticCategory.COMPATIBILITY,
                        message=f"Table '{table.name}' target encryption algorithm 3DES is deprecated and unsupported on target dialect {trans.target_dialect}.",
                        path=f"tables.{table.name}",
                        explanation="Triple DES encryption algorithms are dropped by modern database engines due to vulnerabilities.",
                        root_cause="Deprecated cryptographic primitives.",
                        suggested_fix="Re-encrypt table schema layout using AES256 or ChaCha20.",
                        affected_event=table.name,
                        affected_session=session_id,
                        correlation_id=correlation_id,
                        trace_id=trace_id
                    ))

            # 3. Check Manual Column-Level Migration Requirement (e.g. PostgreSQL)
            if trans.compatibility_tier == EncryptionCompatibilityTier.REQUIRES_MANUAL_MIGRATION:
                diagnostics.append(Diagnostic(
                    diagnostic_code="ENCRYPTION_MANUAL_MIGRATION_REQUIRED",
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.COMPATIBILITY,
                    message=f"Table '{table.name}' requires manual schema/application-level column encryption for PostgreSQL.",
                    path=f"tables.{table.name}",
                    explanation="PostgreSQL lacks native engine-level tablespace TDE. Relies on pgcrypto extensions or client-side crypto.",
                    root_cause="Lack of native TDE support on PostgreSQL target engine.",
                    suggested_fix="Configure pgcrypto extensions on target, or implement application-level column encryption.",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

            # 4. Check Plugin Requirement (e.g. MySQL keyring plugins)
            if trans.compatibility_tier == EncryptionCompatibilityTier.PLUGIN_PROVIDED:
                diagnostics.append(Diagnostic(
                    diagnostic_code="ENCRYPTION_PLUGIN_REQUIRED",
                    severity=Severity.WARNING,
                    category=DiagnosticCategory.COMPATIBILITY,
                    message=f"Table '{table.name}' encryption requires keyring_file or keyring_okv plugin installation on MySQL.",
                    path=f"tables.{table.name}",
                    explanation="MySQL TDE features require activating a keyring management plugin component in the configuration files.",
                    root_cause="Plugin-dependent TDE framework.",
                    suggested_fix="Add early keyring_file plugin load to target MySQL configuration (my.cnf).",
                    affected_event=table.name,
                    affected_session=session_id,
                    correlation_id=correlation_id,
                    trace_id=trace_id
                ))

        return diagnostics

    def validate_startup_config(self, profiles_data: Dict[str, Any]) -> None:
        """Validates configuration profiles JSON structure. Fails fast on startup violations."""
        profiles = profiles_data.get("profiles", [])
        seen_ids: Set[str] = set()

        for idx, prof in enumerate(profiles):
            prof_id = prof.get("profile_id")
            if not prof_id:
                raise EncryptionValidationError(
                    f"Profile at index {idx} is missing 'profile_id'.",
                    error_code="ENCRYPTION_CONFIG_INVALID"
                )

            if prof_id in seen_ids:
                raise EncryptionValidationError(
                    f"Duplicate encryption profile ID detected: {prof_id}",
                    error_code="ENCRYPTION_CONFIG_INVALID"
                )
            seen_ids.add(prof_id)

            min_ver = prof.get("min_version")
            max_ver = prof.get("max_version")
            if min_ver and max_ver:
                if min_ver > max_ver:
                    raise EncryptionValidationError(
                        f"Profile '{prof_id}' version bounds are inverted: min_version {min_ver} > max_version {max_ver}.",
                        error_code="ENCRYPTION_CONFIG_INVALID"
                    )
