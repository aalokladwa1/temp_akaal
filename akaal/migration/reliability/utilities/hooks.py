from typing import Callable, List, Any
from akaal.migration.reliability.context.reliability_context import ReliabilityContext

# Hook registers
_before_validation_hooks: List[Callable[[ReliabilityContext], None]] = []
_after_validation_hooks: List[Callable[[ReliabilityContext, Any], None]] = []

_before_health_check_hooks: List[Callable[[ReliabilityContext], None]] = []
_after_health_check_hooks: List[Callable[[ReliabilityContext, Any], None]] = []

_before_simulation_hooks: List[Callable[[ReliabilityContext], None]] = []
_after_simulation_hooks: List[Callable[[ReliabilityContext, Any], None]] = []

_before_certification_hooks: List[Callable[[ReliabilityContext], None]] = []
_after_certification_hooks: List[Callable[[ReliabilityContext, Any], None]] = []

_before_rollback_generation_hooks: List[Callable[[ReliabilityContext], None]] = []
_after_rollback_generation_hooks: List[Callable[[ReliabilityContext, Any], None]] = []


def before_validation(context: ReliabilityContext) -> None:
    for h in _before_validation_hooks:
        h(context)

def after_validation(context: ReliabilityContext, report: Any) -> None:
    for h in _after_validation_hooks:
        h(context, report)

def before_health_check(context: ReliabilityContext) -> None:
    for h in _before_health_check_hooks:
        h(context)

def after_health_check(context: ReliabilityContext, report: Any) -> None:
    for h in _after_health_check_hooks:
        h(context, report)

def before_simulation(context: ReliabilityContext) -> None:
    for h in _before_simulation_hooks:
        h(context)

def after_simulation(context: ReliabilityContext, report: Any) -> None:
    for h in _after_simulation_hooks:
        h(context, report)

def before_certification(context: ReliabilityContext) -> None:
    for h in _before_certification_hooks:
        h(context)

def after_certification(context: ReliabilityContext, report: Any) -> None:
    for h in _after_certification_hooks:
        h(context, report)

def before_rollback_generation(context: ReliabilityContext) -> None:
    for h in _before_rollback_generation_hooks:
        h(context)

def after_rollback_generation(context: ReliabilityContext, report: Any) -> None:
    for h in _after_rollback_generation_hooks:
        h(context, report)
