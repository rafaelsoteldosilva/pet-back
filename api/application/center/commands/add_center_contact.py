# api/application/center/commands/add_center_contact.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from api.application.center.errors import VeterinaryCenterNotFoundError
from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import (
    Center_Contact,
    Center_Staff_Member,
    Veterinary_Center,
)
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import Choices_Center_Contact_Type
from api.shared.utils.normalize_document_id import (
    is_valid_chilean_rut,
    normalize_document_id,
)

CENTER_CONTACT_TYPE_ERROR = "Tipo de contacto inválido."
AUDIT_ACTION_CENTER_CONTACT_CREATED = "CENTER_CONTACT_CREATED"
AUDIT_ENTITY_TYPE_CENTER_CONTACT = "Center_Contact"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _clean_upper_string(value: Any) -> str:
    return _clean_string(value).upper()


def _clean_email(value: Any) -> str:
    return _clean_string(value).lower()


def _bool_from_payload(value: Any, *, default: bool = True) -> bool:
    if value is None:
        return default

    return value is True


def _raise_invalid_document_id() -> None:
    raise ValidationError(
        {
            "document_id": (
                "El documento indicado no es un RUT chileno válido."
            ),
        }
    )


def _validate_document_id_for_database(document_id: str) -> None:
    if not document_id:
        return

    if not is_valid_chilean_rut(document_id):
        _raise_invalid_document_id()


def _clean_document_id(value: Any) -> str:
    document_id = _clean_string(value)

    if not document_id:
        return ""

    normalized_document_id = normalize_document_id(document_id)

    if not normalized_document_id:
        _raise_invalid_document_id()

    _validate_document_id_for_database(normalized_document_id)

    return normalized_document_id


def _get_document_id_from_payload(data: dict[str, Any]) -> str:
    return _clean_document_id(data.get("document_id"))


def _get_center_contact_type_from_payload(data: dict[str, Any]) -> str:
    return _clean_upper_string(data.get("center_contact_type"))


def _validate_center_contact_type(
    center_contact_type: str,
) -> None:
    allowed_values = {
        Choices_Center_Contact_Type.PERSON.value,
        Choices_Center_Contact_Type.INSTITUTION.value,
    }

    if center_contact_type not in allowed_values:
        raise ValidationError(
            {
                "center_contact_type": CENTER_CONTACT_TYPE_ERROR,
            }
        )


def _validate_no_active_duplicate_document_id(
    *,
    center_id: int,
    document_id: str,
) -> None:
    if not document_id:
        return

    duplicate_exists = Center_Contact.objects.filter(
        veterinary_center_id=center_id,
        document_id=document_id,
        soft_deleted_at__isnull=True,
    ).exists()

    if duplicate_exists:
        raise ValidationError(
            {
                "document_id": (
                    "Ya existe un contacto del centro con ese documento."
                )
            }
        )


def _build_center_contact_data(
    *,
    data: dict[str, Any],
    center_contact_type: str,
) -> dict[str, Any]:
    first_name = _clean_string(data.get("first_name"))
    last_name = _clean_string(data.get("last_name"))
    institution_name = _clean_string(data.get("institution_name"))

    if center_contact_type == Choices_Center_Contact_Type.PERSON.value:
        if not first_name and not last_name:
            raise ValidationError(
                {
                    "first_name": (
                        "Debes indicar al menos nombre o apellido para una persona."
                    ),
                    "last_name": (
                        "Debes indicar al menos nombre o apellido para una persona."
                    ),
                }
            )

        institution_name = ""

    elif center_contact_type == Choices_Center_Contact_Type.INSTITUTION.value:
        if not institution_name:
            raise ValidationError(
                {
                    "institution_name": (
                        "El nombre de la institución es obligatorio."
                    ),
                }
            )

        first_name = ""
        last_name = ""

    else:
        raise ValidationError(
            {
                "center_contact_type": CENTER_CONTACT_TYPE_ERROR,
            }
        )

    return {
        "center_contact_type": center_contact_type,
        "first_name": first_name,
        "last_name": last_name,
        "institution_name": institution_name,
        "document_id": _get_document_id_from_payload(data),
        "email": _clean_email(data.get("email")),
        "primary_phone": _clean_string(data.get("primary_phone")),
        "secondary_phone": _clean_string(data.get("secondary_phone")),
        "tertiary_phone": _clean_string(data.get("tertiary_phone")),
        "address": _clean_string(data.get("address")),
        "city": _clean_string(data.get("city")),
        "region": _clean_string(data.get("region")),
        "country": _clean_string(data.get("country")),
        "notes": _clean_string(
            data.get("notes") or data.get("center_contact_notes")
        ),
        "is_active": _bool_from_payload(data.get("is_active"), default=True),
    }


def _validate_actor_member_for_center(
    *,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    center_id: int,
) -> None:
    if member.veterinary_center_id != center_id:
        raise PermissionError(
            "La membresía activa no pertenece al centro veterinario indicado."
        )

    if member.user_id != actor.id:
        raise PermissionError(
            "La membresía activa no pertenece al usuario autenticado."
        )

    if not member.is_active:
        raise PermissionError(
            "La membresía del usuario en este centro no está activa."
        )

    if not member.veterinary_center.is_active:
        raise PermissionError(
            "El centro veterinario no está activo."
        )


def _get_actor_display_name(actor: Pet_Control_User) -> str:
    get_full_name = getattr(actor, "get_full_name", None)

    if callable(get_full_name):
        full_name = _clean_string(get_full_name())

        if full_name:
            return full_name

    get_username = getattr(actor, "get_username", None)

    if callable(get_username):
        username = _clean_string(get_username())

        if username:
            return username

    email = _clean_string(getattr(actor, "email", ""))

    if email:
        return email

    return f"User {actor.id}"


def _get_member_role(member: Center_Staff_Member) -> str:
    role = getattr(member, "role", "")

    return _clean_string(getattr(role, "value", role))


def _build_center_contact_audit_values(
    center_contact: Center_Contact,
) -> dict[str, Any]:
    return {
        "id": center_contact.id,
        "veterinary_center_id": center_contact.veterinary_center_id,
        "center_contact_type": center_contact.center_contact_type,
        "first_name": center_contact.first_name,
        "last_name": center_contact.last_name,
        "institution_name": center_contact.institution_name,
        "document_id": center_contact.document_id,
        "email": center_contact.email,
        "primary_phone": center_contact.primary_phone,
        "secondary_phone": center_contact.secondary_phone,
        "tertiary_phone": center_contact.tertiary_phone,
        "address": center_contact.address,
        "city": center_contact.city,
        "region": center_contact.region,
        "country": center_contact.country,
        "notes": center_contact.notes,
        "is_active": center_contact.is_active,
    }


def _create_center_contact_created_audit_log(
    *,
    center_contact: Center_Contact,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=center_contact.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_CENTER_CONTACT_CREATED,
        entity_type=AUDIT_ENTITY_TYPE_CENTER_CONTACT,
        entity_id=center_contact.id,
        reason=_clean_string(reason),
        old_values={},
        new_values=_build_center_contact_audit_values(center_contact),
    )


@transaction.atomic
def add_center_contact(
    *,
    center_id: int,
    data: dict[str, Any],
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None = None,
) -> Center_Contact:
    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=center_id,
    )

    try:
        veterinary_center = Veterinary_Center.objects.get(id=center_id)
    except Veterinary_Center.DoesNotExist as exc:
        raise VeterinaryCenterNotFoundError(
            f"Veterinary center with id {center_id} was not found."
        ) from exc

    center_contact_type = _get_center_contact_type_from_payload(data)

    _validate_center_contact_type(center_contact_type)

    center_contact_data = _build_center_contact_data(
        data=data,
        center_contact_type=center_contact_type,
    )

    _validate_no_active_duplicate_document_id(
        center_id=center_id,
        document_id=center_contact_data["document_id"],
    )

    center_contact = Center_Contact(
        veterinary_center=veterinary_center,
        **center_contact_data,
    )

    center_contact.full_clean()
    center_contact.save()

    _create_center_contact_created_audit_log(
        center_contact=center_contact,
        actor=actor,
        member=member,
        reason=reason,
    )

    return center_contact


__all__ = [
    "add_center_contact",
]