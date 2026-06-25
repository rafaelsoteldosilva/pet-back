# api/interfaces/http/presenters/to_jsonable.py

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def _is_dataclass_instance(value: Any) -> bool:
    return is_dataclass(value) and not isinstance(value, type)


def to_jsonable(value: Any) -> Any:
    """
    Converts DTOs/dataclasses and other Python objects into JSON-safe values
    that can be returned by DRF Response().
    """

    if value is None:
        return None

    if _is_dataclass_instance(value):
        return {
            field.name: to_jsonable(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, dict):
        return {
            str(key): to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            to_jsonable(item)
            for item in value
        ]

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return value


__all__ = [
    "to_jsonable",
]