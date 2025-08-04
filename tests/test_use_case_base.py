from __future__ import annotations

import asyncio

import pytest

from hexaframe.errors import Conflict, HexaError, ValidationError
from hexaframe.result import Err, Ok, Result
from hexaframe.use_case import AsyncUseCase, UseCase

# ----------------------------
# Sync UseCase
# ----------------------------


class AddOne(UseCase[int, int]):
    def validate(self, input: int) -> None:
        if input < 0:
            raise ValidationError("must be non-negative", {"value": input})

    def before(self, input: int) -> None:
        # no-op hook, just ensure hook path doesn't blow up
        self._before_seen = True  # type: ignore[attr-defined]

    def after(self, result: Result[int, HexaError]) -> None:
        self._after_seen = True  # type: ignore[attr-defined]

    def perform(self, input: int) -> int:
        return input + 1


def test_sync_use_case_success():
    uc = AddOne()
    res = uc.execute(1)
    assert isinstance(res, Ok)
    assert res.unwrap() == 2
    assert getattr(uc, "_before_seen", False)
    assert getattr(uc, "_after_seen", False)


def test_sync_use_case_validation_error_to_err():
    uc = AddOne()
    res = uc.execute(-1)
    assert isinstance(res, Err)
    assert res.err is not None
    assert isinstance(res.err, ValidationError)


class FailingUC(UseCase[int, int]):
    def perform(self, input: int) -> int:
        raise Conflict("conflict happened")


def test_sync_use_case_catches_hexaerror_to_err():
    uc = FailingUC()
    res = uc.execute(1)
    assert isinstance(res, Err)
    assert isinstance(res.err, Conflict)


class UnexpectedExceptionUC(UseCase[int, int]):
    def perform(self, input: int) -> int:
        raise RuntimeError("boom")


def test_sync_use_case_propagates_non_hexaerror():
    uc = UnexpectedExceptionUC()
    with pytest.raises(RuntimeError):
        uc.execute(0)


# ----------------------------
# Async UseCase
# ----------------------------


class AsyncAddOne(AsyncUseCase[int, int]):
    async def avalidate(self, input: int) -> None:
        if input < 0:
            raise ValidationError("must be non-negative", {"value": input})

    async def abefore(self, input: int) -> None:
        self._before_seen = True  # type: ignore[attr-defined]

    async def aafter(self, result: Result[int, HexaError]) -> None:
        self._after_seen = True  # type: ignore[attr-defined]

    async def aperform(self, input: int) -> int:
        await asyncio.sleep(0)  # ensure awaits are fine
        return input + 1


@pytest.mark.asyncio
async def test_async_use_case_success():
    uc = AsyncAddOne()
    res = await uc.execute(2)
    assert isinstance(res, Ok)
    assert res.unwrap() == 3
    assert getattr(uc, "_before_seen", False)
    assert getattr(uc, "_after_seen", False)


class AsyncFailingUC(AsyncUseCase[int, int]):
    async def aperform(self, input: int) -> int:
        raise Conflict("nope")


@pytest.mark.asyncio
async def test_async_use_case_catches_hexaerror_to_err():
    uc = AsyncFailingUC()
    res = await uc.execute(0)
    assert isinstance(res, Err)
    assert isinstance(res.err, Conflict)


class AsyncUnexpectedExceptionUC(AsyncUseCase[int, int]):
    async def aperform(self, input: int) -> int:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_async_use_case_propagates_non_hexaerror():
    uc = AsyncUnexpectedExceptionUC()
    with pytest.raises(RuntimeError):
        await uc.execute(0)
