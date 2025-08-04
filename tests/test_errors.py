from __future__ import annotations

import pytest

from hexaframe.errors import (
    Conflict,
    DomainError,
    HexaError,
    InfraError,
    NotFound,
    PermissionDenied,
    ValidationError,
)


def test_error_hierarchy_and_str():
    e = ValidationError("bad input", {"field": "name"})
    assert isinstance(e, HexaError)
    assert isinstance(e, DomainError)
    assert e.code == "validation_error"
    assert "validation_error: bad input" in str(e)
    assert "field" in str(e)


def test_not_found_conflict_permission():
    nf = NotFound()
    cf = Conflict("already exists")
    pd = PermissionDenied()
    assert nf.code == "not_found"
    assert cf.code == "conflict"
    assert pd.code == "permission_denied"


def test_infra_error_is_distinct():
    ioe = InfraError(code="io_error", message="disk full")
    assert isinstance(ioe, HexaError)
    assert not isinstance(ioe, DomainError)
    assert ioe.code == "io_error"
    assert "disk full" in str(ioe)


def test_raise_and_catch_hexaerror():
    with pytest.raises(HexaError):
        raise Conflict("boom")
