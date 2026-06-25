# api/interfaces/http/presenters/center/center_vet_presenter.py

from __future__ import annotations

from typing import Any

from api.infrastructure.orm.models.center import Center_Staff_Membership
from api.interfaces.http.presenters.center.veterinary_center_presenter import (
    veterinary_center_presenter,
)


def _first_text_value(*values: Any) -> str:
    for value in values:
        if value is None:
            continue

        text_value = str(value).strip()

        if text_value:
            return text_value

    return ""


def _first_optional_text_value(*values: Any) -> str | None:
    value = _first_text_value(*values)

    if not value:
        return None

    return value


def _build_full_name(
    *,
    first_name: str,
    last_name: str,
    fallback_email: str,
) -> str:
    full_name = f"{first_name} {last_name}".strip()

    if full_name:
        return full_name

    return fallback_email


def center_vet_presenter(
    center_vet: Center_Staff_Membership,
) -> dict[str, Any]:
    user = center_vet.user

    first_name = _first_text_value(
        getattr(user, "first_name", None),
        getattr(center_vet, "first_name", None),
    )

    last_name = _first_text_value(
        getattr(user, "last_name", None),
        getattr(center_vet, "last_name", None),
    )

    email = _first_text_value(
        getattr(center_vet, "work_email", None),
        getattr(user, "email", None),
        getattr(center_vet, "email", None),
    )

    return {
        "id": center_vet.id,
        "first_name": first_name,
        "last_name": last_name,
        "full_name": _build_full_name(
            first_name=first_name,
            last_name=last_name,
            fallback_email=email,
        ),
        "email": email,
        "country_code": _first_text_value(
            getattr(user, "country_code", None),
            getattr(center_vet, "country_code", None),
        ),
        "document_id": _first_text_value(
            getattr(user, "document_id", None),
            getattr(center_vet, "document_id", None),
        ),
        "cell_phone": _first_optional_text_value(
            getattr(center_vet, "work_phone", None),
            getattr(user, "cell_phone", None),
            getattr(center_vet, "cell_phone", None),
        ),
        "complete_address": _first_optional_text_value(
            getattr(user, "complete_address", None),
            getattr(center_vet, "complete_address", None),
        ),
        "role": center_vet.role,
        "veterinary_center": veterinary_center_presenter(
            center_vet.veterinary_center,
        ),
    }


def list_of_center_vets_presenter(
    center_vets: list[Center_Staff_Membership],
) -> list[dict[str, Any]]:
    return [
        center_vet_presenter(center_vet)
        for center_vet in center_vets
    ]