"""
akaalEngine.data_processing.engine.processing_engine
======================================================
Core ProcessingEngine executing compiled ProcessingPlan over row batches and CDC change-images.
Mined from `akaal/transformation/engine.py` & `akaal/privacy/engine.py`.
"""

import logging
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from akaalEngine.data_processing.cleansing.engine import CleansingEngine
from akaalEngine.data_processing.dedup.deduplicator import RowDeduplicator
from akaalEngine.data_processing.engine.expression_compiler import ExpressionCompiler
from akaalEngine.data_processing.engine.lookup_resolver import LookupResolver
from akaalEngine.data_processing.lob.boundary import LOBMaterializationGuard
from akaalEngine.data_processing.models.errors import MalformedDataException
from akaalEngine.data_processing.models.plan import (
    MalformedDataPolicy,
    ProcessingPlan,
    RuleType,
)
from akaalEngine.data_processing.models.result import (
    ChangeImageResult,
    ProcessingResult,
    TransformationDiagnostic,
)
from akaalEngine.data_processing.privacy.masking import MaskingEngine

logger = logging.getLogger("akaalEngine.data_processing.engine.processing_engine")


class ProcessingEngine:
    """Canonical processing execution engine."""

    def __init__(
        self,
        lookup_resolver: Optional[LookupResolver] = None,
        deduplicator: Optional[RowDeduplicator] = None,
        secret_resolver: Optional[Callable[[str], bytes]] = None,
    ) -> None:
        self.lookup_resolver = lookup_resolver or LookupResolver()
        self.deduplicator = deduplicator or RowDeduplicator()
        self.secret_resolver = secret_resolver
        self.lob_guard = LOBMaterializationGuard()

    def transform_row(self, row: Mapping[str, Any], plan: ProcessingPlan) -> ProcessingResult:
        """Transforms a single row dictionary according to compiled ProcessingPlan."""
        # 1. Evaluate Selective Filter Predicate
        if plan.filter_predicate:
            if not bool(ExpressionCompiler.evaluate(plan.filter_predicate, row)):
                return ProcessingResult(status="FILTERED", transformed_row=None)

        # 2. Bounded Deduplication Check
        if plan.dedup_key_columns:
            if self.deduplicator.is_duplicate(row, plan.dedup_key_columns):
                return ProcessingResult(status="FILTERED", transformed_row=None)

        new_row = dict(row)
        diagnostics: List[TransformationDiagnostic] = []

        # 3. Execute Compiled Transformation Rules
        for rule in plan.compiled_rules:
            col = rule.column_name
            target_col = rule.target_column_name or col

            try:
                # Check LOB Safety
                if col in new_row:
                    self.lob_guard.check_value_safety(col, new_row[col])

                # A. Column Mapping & Rename
                if rule.rule_type == RuleType.MAPPING:
                    val = new_row.get(col)
                    if target_col != col:
                        new_row[target_col] = val
                        new_row.pop(col, None)

                # B. Cleansing / Normalization
                elif rule.rule_type == RuleType.CLEANSING and rule.cleansing_operation:
                    val = new_row.get(col)
                    new_row[target_col] = CleansingEngine.apply_cleansing(
                        rule.cleansing_operation, val, default_val=rule.default_value
                    )

                # C. AST Expression Engine
                elif rule.rule_type == RuleType.EXPRESSION and rule.expression_ast:
                    new_row[target_col] = ExpressionCompiler.evaluate(rule.expression_ast, new_row)

                # D. Lookup Table Resolution
                elif rule.rule_type == RuleType.LOOKUP and rule.lookup_definition:
                    self.lookup_resolver.register_lookup(rule.lookup_definition)
                    src_val = new_row.get(col)
                    resolved_val, policy_action = self.lookup_resolver.resolve(
                        rule.lookup_definition.lookup_name, src_val
                    )
                    if policy_action == "QUARANTINE_RECORD":
                        diag = TransformationDiagnostic(
                            level="WARNING",
                            code="LOOKUP_KEY_QUARANTINED",
                            message=f"Key '{src_val}' missing in lookup '{rule.lookup_definition.lookup_name}'",
                            column_name=col,
                            rule_id=rule.rule_id,
                        )
                        return ProcessingResult(
                            status="QUARANTINED",
                            transformed_row=None,
                            diagnostics=[diag],
                            quarantine_metadata={
                                "rule_id": rule.rule_id,
                                "column_name": col,
                                "original_value": src_val,
                                "reason": diag.message,
                            },
                        )
                    new_row[target_col] = resolved_val

                # E. Privacy / Masking Engine
                elif rule.rule_type == RuleType.PRIVACY and rule.privacy_strategy:
                    val = new_row.get(col)
                    new_row[target_col] = MaskingEngine.apply_mask(
                        strategy=rule.privacy_strategy,
                        value=val,
                        mask_char=rule.mask_char,
                        unmasked_length=rule.unmasked_length,
                        secret_resolver=self.secret_resolver,
                        key_ref=rule.privacy_key_ref,
                    )

                # F. Default Value Assignment
                elif rule.rule_type == RuleType.DEFAULT:
                    if new_row.get(col) is None:
                        new_row[target_col] = rule.default_value

                # G. Data Quality Rule Engine
                elif rule.rule_type == RuleType.QUALITY:
                    val = new_row.get(col)
                    qtype = str(rule.quality_rule_type or "NOT_NULL").upper()

                    # 1. NOT_NULL Check
                    if qtype == "NOT_NULL" and val is None:
                        raise ValueError(f"Quality rule violation: Column '{col}' is NULL, but NOT_NULL rule '{rule.rule_id}' is configured.")

                    # 2. MAX_LENGTH & Truncation Check
                    elif qtype == "MAX_LENGTH" and val is not None and rule.max_length is not None:
                        s_val = str(val)
                        if len(s_val) > rule.max_length:
                            if rule.allow_truncation or rule.malformed_policy == MalformedDataPolicy.EXPLICIT_TRUNCATE:
                                new_row[target_col] = s_val[:rule.max_length]
                                diagnostics.append(TransformationDiagnostic(
                                    level="WARNING",
                                    code="EXPLICIT_TRUNCATION",
                                    message=f"Column '{col}' explicitly truncated to max length {rule.max_length}.",
                                    column_name=col,
                                    rule_id=rule.rule_id,
                                ))
                            else:
                                raise ValueError(
                                    f"Quality rule violation: Column '{col}' length {len(s_val)} exceeds maximum allowed {rule.max_length}."
                                )

                    # 3. NUMERIC_OVERFLOW Check
                    elif qtype == "NUMERIC_OVERFLOW" and val is not None:
                        try:
                            num_val = float(val)
                        except (ValueError, TypeError):
                            raise ValueError(f"Quality rule violation: Column '{col}' value '{val}' is not numeric.")

                        target_dt = str(rule.target_datatype or "INT").upper()
                        bounds = {
                            "SMALLINT": (-32768, 32767),
                            "INT": (-2147483648, 2147483647),
                            "INTEGER": (-2147483648, 2147483647),
                            "BIGINT": (-9223372036854775808, 9223372036854775807),
                            "TINYINT": (0, 255),
                        }
                        if target_dt in bounds:
                            b_min, b_max = bounds[target_dt]
                            if num_val < b_min or num_val > b_max:
                                raise ValueError(
                                    f"Quality rule violation: Column '{col}' value {num_val} overflows target {target_dt} bounds [{b_min}, {b_max}]."
                                )
                        if rule.min_value is not None and num_val < float(rule.min_value):
                            raise ValueError(f"Quality rule violation: Column '{col}' value {num_val} is below minimum {rule.min_value}.")
                        if rule.max_value is not None and num_val > float(rule.max_value):
                            raise ValueError(f"Quality rule violation: Column '{col}' value {num_val} exceeds maximum {rule.max_value}.")

                    # 4. VALUE_RANGE Check
                    elif qtype == "VALUE_RANGE" and val is not None:
                        try:
                            num_val = float(val)
                            if rule.min_value is not None and num_val < float(rule.min_value):
                                raise ValueError(f"Quality rule violation: Column '{col}' value {num_val} is below minimum {rule.min_value}.")
                            if rule.max_value is not None and num_val > float(rule.max_value):
                                raise ValueError(f"Quality rule violation: Column '{col}' value {num_val} exceeds maximum {rule.max_value}.")
                        except (ValueError, TypeError) as err:
                            raise ValueError(f"Quality rule range check failed on column '{col}': {err}")

                    # 5. REGEX_MATCH Check
                    elif qtype == "REGEX_MATCH" and val is not None and rule.regex_pattern:
                        import re
                        s_val = str(val)
                        if not re.match(rule.regex_pattern, s_val):
                            raise ValueError(f"Quality rule violation: Column '{col}' value does not match regex pattern.")

                    # 6. ENUM_VALUES Check
                    elif qtype == "ENUM_VALUES" and val is not None and rule.allowed_values:
                        if val not in rule.allowed_values and str(val) not in [str(x) for x in rule.allowed_values]:
                            raise ValueError(f"Quality rule violation: Column '{col}' value '{val}' not in allowed enum values.")

            except Exception as exc:
                diag = TransformationDiagnostic(
                    level="BLOCKER",
                    code="PROCESSING_FAILURE",
                    message=f"Rule '{rule.rule_id}' failed on column '{col}': {exc}",
                    column_name=col,
                    rule_id=rule.rule_id,
                )
                diagnostics.append(diag)

                policy = rule.malformed_policy
                if policy == MalformedDataPolicy.FAIL_JOB:
                    raise MalformedDataException(col, rule.rule_id, str(exc))
                elif policy == MalformedDataPolicy.REJECT_RECORD:
                    return ProcessingResult(status="REJECTED", transformed_row=None, diagnostics=diagnostics)
                elif policy == MalformedDataPolicy.QUARANTINE_RECORD:
                    return ProcessingResult(
                        status="QUARANTINED",
                        transformed_row=None,
                        diagnostics=diagnostics,
                        quarantine_metadata={
                            "rule_id": rule.rule_id,
                            "column_name": col,
                            "original_value": new_row.get(col),
                            "reason": diag.message,
                        },
                    )
                elif policy == MalformedDataPolicy.USE_DEFAULT:
                    new_row[target_col] = rule.default_value
                elif policy == MalformedDataPolicy.USE_NULL:
                    new_row[target_col] = None

        return ProcessingResult(status="SUCCESS", transformed_row=new_row, diagnostics=diagnostics)

    def transform_batch(
        self, batch: Sequence[Mapping[str, Any]], plan: ProcessingPlan
    ) -> Tuple[List[Dict[str, Any]], List[ProcessingResult]]:
        """Transforms a batch of row dictionaries deterministically with optional batch deduplication."""
        input_records = list(batch)

        # Batch-level deduplication with deterministic survivor selection
        if plan.dedup_key_columns and len(input_records) > 1:
            survivors, duplicates, _ = self.deduplicator.deduplicate_batch(
                records=input_records,
                key_columns=plan.dedup_key_columns,
                survivor_strategy=plan.survivor_strategy,
                order_by_columns=plan.order_by_columns,
                priority_field=plan.priority_field,
                priority_order=plan.priority_order,
                disposition=plan.dedup_disposition,
            )
            input_records = survivors

        transformed_rows: List[Dict[str, Any]] = []
        results: List[ProcessingResult] = []

        for row in input_records:
            res = self.transform_row(row, plan)
            results.append(res)
            if res.status == "SUCCESS" and res.transformed_row is not None:
                transformed_rows.append(res.transformed_row)


        return transformed_rows, results

    def transform_change_image(self, change_payload: Dict[str, Any], plan: ProcessingPlan) -> ChangeImageResult:
        """Transforms CDC row image payload (after_image / before_image) while preserving key identity."""
        new_payload = dict(change_payload)
        after_img = new_payload.get("after_image") or new_payload.get("data")

        if after_img and isinstance(after_img, dict):
            res = self.transform_row(after_img, plan)
            if res.status == "SUCCESS" and res.transformed_row is not None:
                if "after_image" in new_payload:
                    new_payload["after_image"] = res.transformed_row
                elif "data" in new_payload:
                    new_payload["data"] = res.transformed_row
                return ChangeImageResult(status="SUCCESS", transformed_image=new_payload)
            elif res.status in ("REJECTED", "QUARANTINED"):
                return ChangeImageResult(
                    status=res.status,
                    transformed_image=None,
                    is_quarantined=True,
                    quarantine_reason=res.diagnostics[0].message if res.diagnostics else "CDC Row Quarantined",
                )

        return ChangeImageResult(status="SUCCESS", transformed_image=new_payload)
