# api/interfaces/http/presenters/pet/all_pets_for_center_presenter.py

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from api.application.pet.dto.pet_data_dto import (
    Pet_Data_DTO,
)


JsonDict = dict[str, Any]


def all_pets_for_center_presenter(
    dto: Pet_Data_DTO,
) -> JsonDict:
    """
    Presenter for the pets list/search endpoint.

    Important:
    - dto.birth_date may arrive as str | None from the application DTO.
    - Do not call dto.birth_date.isoformat() directly.
    - Use _present_date() so the presenter is safe whether the DTO gives
      str, date, datetime, or None.
    """

    return {
        "id": dto.id,
        "history_code": dto.history_code,
        "name": dto.name,
        "sex": _present_enum_value(dto.sex),
        "sex_label": dto.sex_label,
        "species": _present_species(dto.species),
        "breed": _present_breed(dto.breed),
        "sterilized": dto.sterilized,
        "birth_date": _present_date(dto.birth_date),
        "body_description": dto.body_description,
        "size": _present_enum_value(dto.size),
        "last_weight": _present_decimal(dto.last_weight),
        "last_attending_vet": _present_personnel(dto.last_attending_vet),
        "reference": dto.reference,
        "has_pedigree": dto.has_pedigree,
        "pedigree_registry": dto.pedigree_registry,
        "has_visual_identification": dto.has_visual_identification,
        "visual_tag": dto.visual_tag,
        "visual_identification_or_tattoo_description": (
            dto.visual_identification_or_tattoo_description
        ),
        "has_microchip": dto.has_microchip,
        "microchip_code": dto.microchip_code,
        "microchip_date": _present_date(dto.microchip_date),
        "microchip_body_region": dto.microchip_body_region,
        "clinical_observations": dto.clinical_observations,
        "internal_notes": dto.internal_notes,
        "photo_url": dto.photo_url,
        "status": _present_enum_value(dto.status),
        "clinical_record_status": _present_enum_value(dto.clinical_record_status),
        "veterinary_center": _present_veterinary_center(dto.veterinary_center),
        "contact_links": [
            _present_pet_contact_link(contact_link)
            for contact_link in dto.contact_links
        ],
    }


def present_search_pets_list(
    dtos: list[Pet_Data_DTO],
) -> list[JsonDict]:
    return [
        all_pets_for_center_presenter(dto)
        for dto in dtos
    ]


def _present_date(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        clean_value = value.strip()

        return clean_value or None

    return str(value)


def _present_decimal(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _present_enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    return value


def _present_species(species: Any) -> JsonDict | None:
    if species is None:
        return None

    return {
        "id": _get_value(species, "id"),
        "name": _get_value(species, "name"),
    }


def _present_breed(breed: Any) -> JsonDict | None:
    if breed is None:
        return None

    return {
        "id": _get_value(breed, "id"),
        "name": _get_value(breed, "name"),
    }


def _present_personnel(personnel: Any) -> JsonDict | None:
    if personnel is None:
        return None

    return {
        "id": _get_value(personnel, "id"),
        "name": _get_first_value(
            personnel,
            ("name", "full_name", "display_name"),
        ),
    }


def _present_veterinary_center(veterinary_center: Any) -> JsonDict | None:
    if veterinary_center is None:
        return None

    return {
        "id": _get_value(veterinary_center, "id"),
        "name": _get_value(veterinary_center, "name"),
    }


def _present_pet_contact_link(contact_link: Any) -> JsonDict:
    """
    Presents a Pet_Contact_Link.

    The Pet_Contact_Link contains the relationship data between the pet and
    the reusable Center_Contact record.
    """

    center_contact = _get_value(contact_link, "center_contact")

    return {
        "id": _get_value(contact_link, "id"),
        "role": _present_enum_value(_get_value(contact_link, "role")),
        "role_label": _get_value(contact_link, "role_label"),
        "specific_relationship": _get_value(
            contact_link,
            "specific_relationship",
        ),
        "is_primary_contact": _get_bool(
            contact_link,
            "is_primary_contact",
        ),
        "is_emergency_contact": _get_bool(
            contact_link,
            "is_emergency_contact",
        ),
        "can_authorize_treatment": _get_bool(
            contact_link,
            "can_authorize_treatment",
        ),
        "can_receive_medical_updates": _get_bool(
            contact_link,
            "can_receive_medical_updates",
        ),
        "can_receive_billing": _get_bool(
            contact_link,
            "can_receive_billing",
        ),
        "can_pickup_pet": _get_bool(
            contact_link,
            "can_pickup_pet",
        ),
        "notes": _get_value(contact_link, "notes"),
        "is_active": _get_bool(
            contact_link,
            "is_active",
            default=True,
        ),
        "center_contact": _present_center_contact(
            center_contact
        ),
    }


def _present_center_contact(
    center_contact: Any,
) -> JsonDict | None:
    if center_contact is None:
        return None

    return {
        "id": _get_value(center_contact, "id"),
        "center_contact_type": _present_enum_value(
            _get_value(center_contact, "center_contact_type"),
        ),
        "display_name": _get_value(center_contact, "display_name"),
        "first_name": _get_value(center_contact, "first_name"),
        "last_name": _get_value(center_contact, "last_name"),
        "institution_name": _get_value(center_contact, "institution_name"),
        "document_id": _get_value(center_contact, "document_id"),
        "email": _get_value(center_contact, "email"),
        "primary_phone": _get_value(center_contact, "primary_phone"),
        "secondary_phone": _get_value(center_contact, "secondary_phone"),
        "tertiary_phone": _get_value(center_contact, "tertiary_phone"),
        "address": _get_value(center_contact, "address"),
        "city": _get_value(center_contact, "city"),
        "region": _get_value(center_contact, "region"),
        "country": _get_value(center_contact, "country"),
        "notes": _get_value(center_contact, "notes"),
        "is_active": _get_bool(
            center_contact,
            "is_active",
            default=True,
        ),
    }


def _get_value(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def _get_first_value(
    obj: Any,
    names: tuple[str, ...],
    default: Any = None,
) -> Any:
    for name in names:
        value = _get_value(obj, name, None)

        if value is not None:
            return value

    return default


def _get_bool(
    obj: Any,
    name: str,
    *,
    default: bool = False,
) -> bool:
    value = _get_value(obj, name, None)

    if value is None:
        return default

    return bool(value)


__all__ = [
    "all_pets_for_center_presenter",
    "present_search_pets_list",
]