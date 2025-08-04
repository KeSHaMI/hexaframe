from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Generic, List, Optional, Sequence, TypeVar

from .ports import ClockPort, LoggerPort, Port, UuidPort

T = TypeVar("T")
ID = TypeVar("ID_contra", bound=Any, contravariant=False)


class InMemoryRepository(Generic[T]):
    """
    Minimal in-memory repository suitable for tests. Stores items by id via extractor.
    """

    def __init__(self, id_of: Callable[[T], Any]):
        self._id_of = id_of
        self._items: Dict[Any, T] = {}

    def add(self, item: T) -> None:
        self._items[self._id_of(item)] = item

    def get(self, id_: Any) -> Optional[T]:
        return self._items.get(id_)

    def remove(self, id_: Any) -> None:
        self._items.pop(id_, None)

    def list(self) -> List[T]:
        return list(self._items.values())

    def clear(self) -> None:
        self._items.clear()


class InMemoryEventBus:
    """
    Simple event bus capturing published events for assertions in tests.
    """

    def __init__(self) -> None:
        self._events: List[Any] = []

    def publish(self, event: Any) -> None:
        self._events.append(event)

    @property
    def events(self) -> Sequence[Any]:
        return tuple(self._events)

    def clear(self) -> None:
        self._events.clear()


@dataclass
class FakeClock(ClockPort):
    """
    Deterministic clock for tests.
    Start at provided 'now' (UTC) and a monotonic seconds baseline.
    """

    now_dt: datetime = field(
        default_factory=lambda: datetime(2024, 1, 1, tzinfo=timezone.utc)
    )
    mono: float = 0.0

    def now(self) -> datetime:
        return self.now_dt

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.mono += seconds
        self.now_dt = self.now_dt + timedelta(seconds=seconds)  # type: ignore[name-defined]


@dataclass
class StubUuid(UuidPort):
    """
    UUID stub that returns a fixed sequence of UUIDs for deterministic tests.
    """

    sequence: List[str] = field(
        default_factory=lambda: ["00000000-0000-4000-8000-000000000000"]
    )
    idx: int = 0

    def uuid4(self) -> uuid.UUID:
        if self.idx >= len(self.sequence):
            # repeat last if out of items
            return uuid.UUID(self.sequence[-1])
        value = uuid.UUID(self.sequence[self.idx])
        self.idx += 1
        return value

    def from_str(self, value: str) -> uuid.UUID:
        return uuid.UUID(value)


class CapturingLogger(LoggerPort):
    """
    Test logger that captures log records for assertions.
    """

    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def _push(self, level: str, msg: str, **fields: Any) -> None:
        rec = {"level": level, "msg": msg, **fields}
        self.records.append(rec)

    def debug(self, msg: str, **fields: Any) -> None:
        self._push("debug", msg, **fields)

    def info(self, msg: str, **fields: Any) -> None:
        self._push("info", msg, **fields)

    def warning(self, msg: str, **fields: Any) -> None:
        self._push("warning", msg, **fields)

    def error(self, msg: str, **fields: Any) -> None:
        self._push("error", msg, **fields)


@dataclass
class TestHarness:
    """
    Lightweight harness to execute use cases with supplied fakes/ports
    and capture results.
    Intended to evolve into a DI/container fixture later.

    Usage:
        harness = TestHarness(clock=fake_clock, uuid=stub_uuid, logger=capturing_logger)
        res = harness.run(UseCaseSubclass(), input)
    """

    clock: Optional[ClockPort] = None
    uuid: Optional[UuidPort] = None
    logger: Optional[LoggerPort] = None

    def provide(self) -> Dict[type, Port]:
        """
        Return a simple mapping from port Protocol to instance for DI wiring.
        Note: This is intentionally minimal and can be extended to integrate with
        hexaframe.di later.
        """
        mapping: Dict[type, Port] = {}
        if self.clock is not None:
            mapping[ClockPort] = self.clock  # type: ignore[assignment]
        if self.uuid is not None:
            mapping[UuidPort] = self.uuid  # type: ignore[assignment]
        if self.logger is not None:
            mapping[LoggerPort] = self.logger  # type: ignore[assignment]
        return mapping
