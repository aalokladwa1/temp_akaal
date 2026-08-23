"""
akaalEngine.extensions.spi.strategy_factory
===========================================
Protocols and wrappers for lazy instantiation and lifecycle management of authority strategies.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class StrategyFactory(Protocol):
    """Protocol for instantiating or obtaining an authority-specific strategy implementation."""
    def __call__(self) -> Any:
        ...


class InstanceStrategyFactory:
    """StrategyFactory wrapping an already instantiated strategy object."""
    def __init__(self, instance: Any) -> None:
        if instance is None:
            raise ValueError("InstanceStrategyFactory requires a non-None strategy instance.")
        self._instance = instance

    def __call__(self) -> Any:
        return self._instance

    def __repr__(self) -> str:
        return f"<InstanceStrategyFactory({type(self._instance).__name__})>"


class LazyTypeStrategyFactory:
    """StrategyFactory that instantiates a class upon first invocation."""
    def __init__(self, cls_or_callable: Callable[[], Any]) -> None:
        if cls_or_callable is None:
            raise ValueError("LazyTypeStrategyFactory requires a non-None factory callable.")
        self._factory = cls_or_callable
        self._cached_instance: Any = None

    def __call__(self) -> Any:
        if self._cached_instance is None:
            self._cached_instance = self._factory()
        return self._cached_instance

    def __repr__(self) -> str:
        return f"<LazyTypeStrategyFactory({self._factory})>"
