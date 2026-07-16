from enum import Enum

class FailurePolicy(str, Enum):
    FAIL_FAST = "fail-fast"
    CONTINUE_INDEPENDENT = "continue-independent"

class RetryPolicyContract:
    """Contract defining scheduler-to-executor retry configurations."""
    def __init__(self, max_retries: int = 3, backoff_seconds: float = 1.0) -> None:
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
