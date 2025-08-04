from __future__ import annotations

import uuid
from dataclasses import dataclass

from hexaframe.testkit import (
    CapturingLogger,
    FakeClock,
    InMemoryEventBus,
    InMemoryRepository,
    StubUuid,
)


@dataclass
class Item:
    id: str
    name: str


def test_in_memory_repository_crud():
    repo = InMemoryRepository[Item](id_of=lambda it: it.id)
    a = Item("1", "a")
    b = Item("2", "b")

    repo.add(a)
    repo.add(b)

    assert repo.get("1") == a
    assert {i.id for i in repo.list()} == {"1", "2"}

    repo.remove("1")
    assert repo.get("1") is None
    assert {i.id for i in repo.list()} == {"2"}

    repo.clear()
    assert repo.list() == []


def test_in_memory_event_bus_captures_events():
    bus = InMemoryEventBus()
    bus.publish({"e": 1})
    bus.publish({"e": 2})
    assert list(bus.events) == [{"e": 1}, {"e": 2}]
    bus.clear()
    assert list(bus.events) == []


def test_fake_clock_advance_and_monotonic():
    clock = FakeClock()
    t0_dt = clock.now()
    t0_mono = clock.monotonic()

    clock.advance(2.5)

    assert clock.monotonic() == t0_mono + 2.5
    assert clock.now() > t0_dt


def test_stub_uuid_sequence_and_repeat_last():
    seq = [
        "00000000-0000-4000-8000-000000000000",
        "00000000-0000-4000-8000-000000000001",
    ]
    stub = StubUuid(sequence=seq)

    u1 = stub.uuid4()
    u2 = stub.uuid4()
    u3 = stub.uuid4()  # repeats last

    assert str(u1) == seq[0]
    assert str(u2) == seq[1]
    assert str(u3) == seq[1]
    assert stub.from_str(seq[0]) == uuid.UUID(seq[0])


def test_capturing_logger_records_levels():
    logger = CapturingLogger()
    logger.debug("d", x=1)
    logger.info("i", k="v")
    logger.warning("w")
    logger.error("e", err="boom")

    levels = [r["level"] for r in logger.records]
    msgs = [r["msg"] for r in logger.records]
    assert levels == ["debug", "info", "warning", "error"]
    assert msgs == ["d", "i", "w", "e"]
    assert logger.records[-1]["err"] == "boom"
