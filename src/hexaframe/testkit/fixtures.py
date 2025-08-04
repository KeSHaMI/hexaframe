"""
Pytest fixtures for HexaFrame TestKit.

Usage:
    # conftest.py or tests using direct import
    from hexaframe.testkit.fixtures import (
        fake_clock,
        stub_uuid,
        event_bus,
        capturing_logger,
        in_memory_repo_factory,
        test_harness,
    )

    def test_example(
        fake_clock,
        stub_uuid,
        event_bus,
        capturing_logger,
        in_memory_repo_factory,
        test_harness,
    ):
        class Entity:
            def __init__(self, id: str, value: int) -> None:
                self.id = id
                self.value = value

        repo = in_memory_repo_factory(lambda e: e.id)
        repo.add(Entity("1", 42))
        assert [e.value for e in repo.list()] == [42]

        # Deterministic time
        t0 = fake_clock.now()
        fake_clock.advance(1.5)
        assert fake_clock.now() > t0

        # Deterministic UUIDs
        _ = stub_uuid.uuid4()

        # Captured logs
        capturing_logger.info("hello", foo="bar")
        assert capturing_logger.records[-1].msg == "hello"

        # TestHarness provides DI mapping of ports
        provided = test_harness.provide()
        assert provided

Fixtures:
- fake_clock: FakeClock
- stub_uuid: StubUuid
- event_bus: InMemoryEventBus
- capturing_logger: CapturingLogger
- in_memory_repo_factory: Callable[[Callable[[T], str]], InMemoryRepository[T]]
- test_harness: TestHarness wired with provided ports
"""

from __future__ import annotations

from typing import Callable, TypeVar

import pytest

from hexaframe.testkit import (
    CapturingLogger,
    FakeClock,
    InMemoryEventBus,
    InMemoryRepository,
    StubUuid,
    TestHarness,
)

T = TypeVar("T")


@pytest.fixture
def fake_clock() -> FakeClock:
    """Deterministic clock for tests (controls now()/monotonic())."""
    return FakeClock()


@pytest.fixture
def stub_uuid() -> StubUuid:
    """Deterministic UUID generator for tests."""
    return StubUuid()


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    """In-memory event bus capturing published events."""
    return InMemoryEventBus()


@pytest.fixture
def capturing_logger() -> CapturingLogger:
    """Logger that records log entries for assertions."""
    return CapturingLogger()


@pytest.fixture
def in_memory_repo_factory() -> Callable[[Callable[[T], str]], InMemoryRepository[T]]:
    """
    Factory to create a generic in-memory repository.

    Example:
        repo = in_memory_repo_factory(lambda e: e.id)
        repo.add(Entity(id="1"))
    """

    def _factory(id_of: Callable[[T], str]) -> InMemoryRepository[T]:
        return InMemoryRepository[T](id_of=id_of)

    return _factory


@pytest.fixture
def test_harness(
    fake_clock: FakeClock, stub_uuid: StubUuid, capturing_logger: CapturingLogger
) -> TestHarness:
    """
    Test harness pre-wired with deterministic ports.
    Provides .provide() -> dict[type, object] for DI-friendly mapping.
    """
    return TestHarness(clock=fake_clock, uuid=stub_uuid, logger=capturing_logger)


__all__ = [
    "fake_clock",
    "stub_uuid",
    "event_bus",
    "capturing_logger",
    "in_memory_repo_factory",
    "test_harness",
]
