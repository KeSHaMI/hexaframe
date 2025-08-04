from __future__ import annotations

from typing import Any, Mapping

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hexaframe.errors import Conflict, ValidationError
from hexaframe.use_case import AsyncUseCase, UseCase
from hexaframe_fastapi import build_router


class AddOneUC(UseCase[dict, dict]):
    def validate(self, input: dict) -> None:
        if "value" not in input:
            raise ValidationError("missing 'value'")
        if not isinstance(input["value"], int):
            raise ValidationError("'value' must be int")

    def perform(self, input: dict) -> dict:
        v = input["value"]
        if v == 41:
            raise Conflict("no 42s allowed")
        return {"result": v + 1}


class AsyncAddOneUC(AsyncUseCase[dict, dict]):
    async def avalidate(self, input: dict) -> None:
        if "value" not in input:
            raise ValidationError("missing 'value'")
        if not isinstance(input["value"], int):
            raise ValidationError("'value' must be int")

    async def aperform(self, input: dict) -> dict:
        v = input["value"]
        if v == 41:
            raise Conflict("no 42s allowed")
        return {"result": v + 1}


def parse_input(body: Mapping[str, Any]) -> dict:
    return dict(body)


def make_app(usecase):
    app = FastAPI()
    app.include_router(
        build_router(
            path="/add-one",
            method="post",
            use_case=usecase,
            input_parser=parse_input,
            output_mapper=lambda out: out,
        )
    )
    return app


def test_sync_ok():
    app = make_app(AddOneUC())
    client = TestClient(app)
    res = client.post("/add-one", json={"value": 1})
    assert res.status_code == 200
    assert res.json() == {"result": 2}


def test_sync_validation_error_422():
    app = make_app(AddOneUC())
    client = TestClient(app)
    res = client.post("/add-one", json={})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "validation_error"


def test_sync_conflict_409():
    app = make_app(AddOneUC())
    client = TestClient(app)
    res = client.post("/add-one", json={"value": 41})
    assert res.status_code == 409
    body = res.json()
    assert body["error"]["code"] == "conflict"


@pytest.mark.asyncio
async def test_async_ok():
    app = make_app(AsyncAddOneUC())
    client = TestClient(app)
    res = client.post("/add-one", json={"value": 2})
    assert res.status_code == 200
    assert res.json() == {"result": 3}
