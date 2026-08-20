"""akaalPipeline.recovery.retry
==============================
Retry policy evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from typing import Set
from akaalPipeline.contracts.enums import PipelineErrorCode


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 3
    retryable_error_codes: Set[PipelineErrorCode] = field(
        default_factory=lambda: {
            PipelineErrorCode.UNAVAILABLE,
            PipelineErrorCode.NOT_READY,
            PipelineErrorCode.INTERNAL_ERROR,
            PipelineErrorCode.PERSISTENCE_FAILURE,
        }
    )


class RetryPolicyEvaluator:
    @staticmethod
    def should_retry(error_code: PipelineErrorCode, current_retry_count: int, policy: RetryPolicy = RetryPolicy()) -> bool:
        if current_retry_count >= policy.max_retries:
            return False
        return error_code in policy.retryable_error_codes
