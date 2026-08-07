from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class FilterStrategy(Protocol):
    def name(self) -> str: ...


FilterFactory = Callable[[], FilterStrategy]


class FilterRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, FilterFactory] = {}

    def register(self, name: str, factory: FilterFactory) -> None:
        if name in self._factories:
            raise ValueError(f"filter already registered: {name}")
        self._factories[name] = factory

    def create(self, name: str) -> FilterStrategy:
        try:
            return self._factories[name]()
        except KeyError as exc:
            raise ValueError(f"filter not registered: {name}") from exc
