from __future__ import annotations

from hexaframe.result import Err, Ok, Result


def test_ok_basics():
    r: Result[int, str] = Ok(10)
    assert r.is_ok()
    assert not r.is_err()
    assert r.ok == 10
    assert r.err is None
    assert r.unwrap() == 10
    assert r.unwrap_or(5) == 10
    assert r.map(lambda x: x + 1) == Ok(11)
    assert r.and_then(lambda x: Ok(x * 2)) == Ok(20)


def test_err_basics():
    r: Result[int, str] = Err("boom")
    assert r.is_err()
    assert not r.is_ok()
    assert r.err == "boom"
    assert r.ok is None
    assert r.unwrap_or(5) == 5
    assert r.map(lambda x: x + 1) == Err("boom")
    assert r.map_err(lambda e: f"{e}!") == Err("boom!")


def test_fold():
    r1: Result[int, str] = Ok(3)
    r2: Result[int, str] = Err("x")
    assert r1.fold(lambda v: v + 1, lambda e: -1) == 4
    assert r2.fold(lambda v: v + 1, lambda e: -1) == -1


def test_or_else():
    r1: Result[int, str] = Err("e")
    r2: Result[int, str] = Ok(1)

    def handler(e: str) -> Result[int, int]:
        return Ok(42)

    assert r1.or_else(handler) == Ok(42)
    assert r2.or_else(handler) == Ok(1)
