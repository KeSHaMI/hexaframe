# Testing with HexaFrame TestKit

HexaFrame provides deterministic, lightweight testing utilities aligned with hexagonal architecture. Use them to unit test UseCases and integration-test adapters with minimal boilerplate.

This guide covers:
- Available fixtures and utilities
- Quickstart with pytest
- Integration with the DI Container via TestHarness.provide()
- An end-to-end example

## Provided utilities

Core TestKit utilities (available via `hexaframe.testkit`):
- InMemoryRepository[T]: Mutable in-memory repository with CRUD, backed by `id_of` function
- InMemoryEventBus: Captures published events for assertions
- FakeClock: Deterministic `now()` and `monotonic()` with `.advance()`
- StubUuid: Deterministic UUID sequence; repeats last when exhausted; `.from_str()` helper
- CapturingLogger: Captures logs as structured records for assertions
- TestHarness: Composes deterministic ports (ClockPort, UuidPort, LoggerPort) and exposes `.provide()` to DI

Pytest fixtures (via `hexaframe.testkit.fixtures`):
- fake_clock: FakeClock
- stub_uuid: StubUuid
- event_bus: InMemoryEventBus
- capturing_logger: CapturingLogger
- in_memory_repo_factory: Callable[[Callable[[T], str]], InMemoryRepository[T]]
- test_harness: TestHarness wired with deterministic ports (clock/uuid/logger)

## Quickstart

1) Install pytest (if not already) and ensure your test environment can import `hexaframe`.

2) Use fixtures in your tests:

```python
# tests/test_my_usecase.py
from dataclasses import dataclass
from typing import Callable
from hexaframe.testkit.fixtures import (
    fake_clock,
    stub_uuid,
    in_memory_repo_factory,
    capturing_logger,
)

@dataclass
class Item:
    id: str
    name: str

def id_of_item(x: Item) -> str:
    return x.id

def test_creates_item(
    fake_clock, stub_uuid, in_memory_repo_factory, capturing_logger
):
    repo = in_memory_repo_factory(id_of_item)

    # advance time, control uuid sequence
    fake_clock.advance(seconds=5)
    stub_uuid.set_sequence(["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"])

    # perform operation
    new = Item(id=stub_uuid.next(), name="hello")
    repo.add(new)

    # assert state
    assert repo.get("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa").name == "hello"
    # logger assertions example:
    # capturing_logger.records == [{"level": "info", "msg": "created", "fields": {...}}]
```

3) Use the event bus in integration-flavored tests:

```python
from hexaframe.testkit.fixtures import event_bus

def test_publishes_event(event_bus):
    # domain(...)
    event_bus.publish({"type": "ItemCreated", "id": "1"})
    assert event_bus.events == [{"type": "ItemCreated", "id": "1"}]
```

## DI integration via TestHarness.provide()

If you use the built-in DI container, TestHarness can supply a ready mapping of deterministic ports:

```python
from hexaframe.di import Container
from hexaframe.testkit.fixtures import test_harness

def test_resolve_usecase_with_di(test_harness):
    container = Container().register_many(test_harness.provide())
    # Register domain dependencies too (e.g., repos, buses)
    # container.register(InMemoryRepository[MyEntity], repo)

    usecase = container.resolve(MyUseCase)  # constructed with deterministic ports
    result = usecase.execute(...)
    ...
```

This enables realistic construction with zero per-test wiring for common ports.

## Examples

See `examples/tests_using_fixtures/` for a complete runnable example demonstrating:
- A simple UseCase that uses an in-memory repository, logger, uuid, and clock
- An event emission captured by InMemoryEventBus
- DI resolution using `Container.register_many(test_harness.provide())`

These examples are not included in CI runs and are intended as learning material.
