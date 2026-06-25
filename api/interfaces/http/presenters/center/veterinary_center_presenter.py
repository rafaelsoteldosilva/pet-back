# api/interfaces/http/presenters/center/veterinary_center_presenter.py

from __future__ import annotations

from typing import Any

from api.infrastructure.orm.models.center import Veterinary_Center


def _text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def veterinary_center_presenter(
    veterinary_center: Veterinary_Center | None,
) -> dict[str, Any] | None:
    if veterinary_center is None:
        return None

    return {
        "id": veterinary_center.id,
        "name": _text(veterinary_center.name),
        "country_code": _text(veterinary_center.country_code),
        "email": _text(veterinary_center.email),
        "address": _text(veterinary_center.address),
        "phone": _text(veterinary_center.phone),
        "diagnostic_code_system": _text(
            veterinary_center.diagnostic_code_system,
        ),
    }