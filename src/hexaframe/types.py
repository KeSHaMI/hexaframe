from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, Mapping, NewType

# Common aliases used across the framework

JSON = Dict[str, Any]
Serializable = Dict[str, Any]  # loose alias for payloads meant for transport/logging
ID = NewType("ID", str)
Timestamp = NewType("Timestamp", float)


def to_serializable(obj: Any) -> Any:
    """
    Best-effort conversion of common domain/app objects to serializable forms.

    - dataclasses -> dict
    - enums -> value
    - datetime -> isoformat()
    - objects with `to_dict()` -> that result
    - mappings/sequences -> transformed recursively
    - otherwise return as-is
    """
    # dataclasses
    if is_dataclass(obj):
        return {k: to_serializable(v) for k, v in asdict(obj).items()}

    # enums
    try:
        import enum

        if isinstance(obj, enum.Enum):
            return obj.value
    except Exception:
        pass

    # datetime
    if isinstance(obj, datetime):
        return obj.isoformat()

    # duck-typed to_dict
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        try:
            return to_dict()
        except Exception:
            pass

    # mappings
    if isinstance(obj, Mapping):
        return {k: to_serializable(v) for k, v in obj.items()}

    # sequences (but not str/bytes)
    if isinstance(obj, (list, tuple, set)):
        return [to_serializable(v) for v in obj]

    return obj
