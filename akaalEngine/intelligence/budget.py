"""akaalEngine.intelligence.budget
==================================
Cancellation / timeout / request-budget primitives (P7C brief §P7C.1 "Cancellation/
timeouts", §16 "Budgets"). Deliberately minimal for P7C.1: contracts and enforcement
hooks the kernel checks at well-defined points. A full multi-dimensional budget
system (token/monetary/concurrency budgets scoped to tenant/environment/time period)
is P7C.4/.6 territory and will compose with these primitives rather than replace them.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Optional


class CancellationToken:
    """Thread-safe cooperative cancellation signal. Mirrors the shape already used
    by akaalEngine.validation.api.ValidationAuthority.check_runtime_cancellation_and_fencing
    (duck-typed `is_cancelled()`), so a future Runtime Authority (#6) CancellationToken
    can be passed here interchangeably."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


@dataclass
class RequestBudget:
    """A bounded time budget for a single Intelligence Kernel request. `max_seconds`
    is fixed at construction; `remaining_seconds()`/`is_exceeded()` are always
    computed from wall-clock elapsed time, never mutated externally, so a budget
    cannot be silently extended mid-flight."""

    max_seconds: float
    _started_at: float = field(default_factory=time.monotonic, init=False)

    def __post_init__(self) -> None:
        if self.max_seconds <= 0:
            raise ValueError("RequestBudget.max_seconds must be positive")

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._started_at

    def remaining_seconds(self) -> float:
        return max(0.0, self.max_seconds - self.elapsed_seconds())

    def is_exceeded(self) -> bool:
        return self.elapsed_seconds() >= self.max_seconds


@dataclass(frozen=True)
class TokenBudget:
    """Foundation contract for a token budget dimension (P7C brief §16). Full
    enforcement requires a live model call to report actual token consumption
    back (EXTERNAL_DEFERRED without a live model gateway provider -- see
    akaalEngine.intelligence.gateway); this dataclass and `record_usage`
    establish the contract shape so a real provider adapter has something to
    report into once one exists, rather than leaving token budgeting wholly
    unmodeled."""

    max_tokens: int
    consumed_tokens: int = 0

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("TokenBudget.max_tokens must be positive")
        if self.consumed_tokens < 0:
            raise ValueError("TokenBudget.consumed_tokens cannot be negative")

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.consumed_tokens)

    def is_exceeded(self) -> bool:
        return self.consumed_tokens >= self.max_tokens

    def record_usage(self, tokens: int) -> "TokenBudget":
        if tokens < 0:
            raise ValueError("token usage cannot be negative")
        return TokenBudget(max_tokens=self.max_tokens, consumed_tokens=self.consumed_tokens + tokens)


@dataclass(frozen=True)
class MonetaryBudget:
    """Foundation contract for a monetary (cost) budget dimension (P7C brief
    §16). `currency` is an opaque ISO-4217-shaped string; this module does no
    currency conversion -- a real cost-tracking authority is out of Group-1
    local scope without a live billed provider to measure against."""

    max_amount: float
    currency: str = "USD"
    consumed_amount: float = 0.0

    def __post_init__(self) -> None:
        if self.max_amount <= 0:
            raise ValueError("MonetaryBudget.max_amount must be positive")
        if self.consumed_amount < 0:
            raise ValueError("MonetaryBudget.consumed_amount cannot be negative")

    def remaining(self) -> float:
        return max(0.0, self.max_amount - self.consumed_amount)

    def is_exceeded(self) -> bool:
        return self.consumed_amount >= self.max_amount

    def record_spend(self, amount: float) -> "MonetaryBudget":
        if amount < 0:
            raise ValueError("spend amount cannot be negative")
        return MonetaryBudget(max_amount=self.max_amount, currency=self.currency, consumed_amount=self.consumed_amount + amount)


def check_budget_and_cancellation(
    budget: Optional[RequestBudget],
    cancellation_token: Optional[CancellationToken],
    *,
    token_budget: Optional[TokenBudget] = None,
    monetary_budget: Optional[MonetaryBudget] = None,
) -> None:
    """Single enforcement point the kernel calls before/after producer invocation.
    Raises a typed error rather than allowing an unbounded hang or silent
    truncation -- see akaalEngine.intelligence.models.errors. `token_budget`/
    `monetary_budget` are optional -- a producer with no live model/cost source
    to report usage from simply never supplies them, and this function is a
    no-op for that dimension (never a fabricated pass)."""
    from akaalEngine.intelligence.models.errors import (
        IntelligenceBudgetExceededError,
        IntelligenceCancelledError,
    )

    if cancellation_token is not None and cancellation_token.is_cancelled():
        raise IntelligenceCancelledError("Intelligence request was cancelled.")
    if budget is not None and budget.is_exceeded():
        raise IntelligenceBudgetExceededError(
            f"Intelligence request exceeded its {budget.max_seconds}s budget."
        )
    if token_budget is not None and token_budget.is_exceeded():
        raise IntelligenceBudgetExceededError(
            f"Intelligence request exceeded its {token_budget.max_tokens}-token budget."
        )
    if monetary_budget is not None and monetary_budget.is_exceeded():
        raise IntelligenceBudgetExceededError(
            f"Intelligence request exceeded its {monetary_budget.max_amount} {monetary_budget.currency} budget."
        )
