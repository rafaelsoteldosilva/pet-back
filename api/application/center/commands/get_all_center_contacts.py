# api/application/center/commands/get_all_center_contacts.py

from __future__ import annotations

from typing import Any

from api.application.center.errors import VeterinaryCenterNotFoundError
from api.application.pet.dto.center_contact_dto import (
    Center_Contact_DTO,
)
from api.infrastructure.orm.models.center import (
    Center_Contact,
    Veterinary_Center,
)
from api.shared.choices.choices import Choices_Center_Contact_Type


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    clean_value = str(value).strip()

    return clean_value or None


def _get_center_contact_type(contact: Center_Contact) -> str:
    return str(
        getattr(contact, "center_contact_type", "") or ""
    ).upper()


def _get_institution_name(contact: Center_Contact) -> str | None:
    return _clean_optional_string(
        getattr(contact, "institution_name", None)
    )


def _build_person_display_name(contact: Center_Contact) -> str | None:
    first_name = _clean_optional_string(
        getattr(contact, "first_name", None)
    )
    last_name = _clean_optional_string(
        getattr(contact, "last_name", None)
    )

    display_name = " ".join(
        item for item in (first_name, last_name) if item
    ).strip()

    return display_name or None


def _build_display_name(contact: Center_Contact) -> str | None:
    center_contact_type = _get_center_contact_type(contact)

    if (
        center_contact_type
        == Choices_Center_Contact_Type.INSTITUTION.value
    ):
        return _get_institution_name(contact)

    return _build_person_display_name(contact)


def _to_center_contact_dto(
    contact: Center_Contact,
) -> Center_Contact_DTO:
    center_contact_type = _get_center_contact_type(contact)

    return Center_Contact_DTO(
        id=int(contact.id),
        center_contact_type=center_contact_type,
        display_name=_build_display_name(contact),
        first_name=_clean_optional_string(
            getattr(contact, "first_name", None)
        ),
        last_name=_clean_optional_string(
            getattr(contact, "last_name", None)
        ),
        institution_name=_get_institution_name(contact),
        document_id=_clean_optional_string(
            getattr(contact, "document_id", None)
        ),
        email=_clean_optional_string(
            getattr(contact, "email", None)
        ),
        primary_phone=_clean_optional_string(
            getattr(contact, "primary_phone", None)
        ),
        secondary_phone=_clean_optional_string(
            getattr(contact, "secondary_phone", None)
        ),
        tertiary_phone=_clean_optional_string(
            getattr(contact, "tertiary_phone", None)
        ),
        address=_clean_optional_string(
            getattr(contact, "address", None)
        ),
        city=_clean_optional_string(
            getattr(contact, "city", None)
        ),
        region=_clean_optional_string(
            getattr(contact, "region", None)
        ),
        country=_clean_optional_string(
            getattr(contact, "country", None)
        ),
        notes=_clean_optional_string(
            getattr(contact, "notes", None)
        ),
        is_active=bool(getattr(contact, "is_active", True)),
    )


def get_all_center_contacts(
    *,
    center_id: int,
) -> list[Center_Contact_DTO]:
    center_exists = Veterinary_Center.objects.filter(id=center_id).exists()

    if not center_exists:
        raise VeterinaryCenterNotFoundError(
            f"Veterinary center with id {center_id} was not found."
        )

    contacts = (
        Center_Contact.objects.filter(
            veterinary_center_id=center_id,
            soft_deleted_at__isnull=True,
        )
        .order_by(
            "-is_active",
            "center_contact_type",
            "first_name",
            "last_name",
            "institution_name",
            "id",
        )
    )

    return [
        _to_center_contact_dto(contact)
        for contact in contacts
    ]