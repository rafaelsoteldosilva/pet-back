# api/application/center/commands/update_center_contact.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from api.application.center.errors import (
    CenterContactNotFoundError,
    VeterinaryCenterNotFoundError,
)
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

AUDIT_ACTION_CENTER_CONTACT_UPDATED = "CENTER_CONTACT_UPDATED"
AUDIT_ENTITY_TYPE_CENTER_CONTACT = "Center_Contact"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _clean_email(value: Any) -> str:
    return _clean_string(value).lower()


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _clean_required_string(
    *,
    field_name: str,
    value: Any,
    message: str,
) -> str:
    clean_value = _clean_string(value)

    if not clean_value:
        raise DjangoValidationError(
            {
                field_name: message,
            }
        )

    return clean_value


def _normalize_center_contact_type(value: Any) -> str:
    clean_value = _clean_required_string(
        field_name="center_contact_type",
        value=value,
        message="El tipo de contacto es obligatorio.",
    ).upper()

    valid_values = {
        Choices_Center_Contact_Type.PERSON.value,
        Choices_Center_Contact_Type.INSTITUTION.value,
    }

    if clean_value not in valid_values:
        raise DjangoValidationError(
            {
                "center_contact_type": "Tipo de contacto inválido.",
            }
        )

    return clean_value


def _normalize_document_id(value: Any) -> str:
    document_id = _clean_string(value)

    if not document_id:
        return ""

    normalized_document_id = normalize_document_id(document_id)

    if not normalized_document_id:
        raise DjangoValidationError(
            {
                "document_id": "El documento indicado no es válido.",
            }
        )

    if not is_valid_chilean_rut(normalized_document_id):
        raise DjangoValidationError(
            {
                "document_id": "El documento indicado no es un RUT chileno válido.",
            }
        )

    return normalized_document_id


def _get_value(
    *,
    data: dict[str, Any],
    key: str,
    current_value: Any,
) -> Any:
    if key in data:
        return data[key]

    return current_value


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


def _validate_no_active_duplicate_document_id(
    *,
    center_id: int,
    center_contact_id: int,
    document_id: str,
) -> None:
    if not document_id:
        return

    duplicate_exists = (
        Center_Contact.objects.filter(
            veterinary_center_id=center_id,
            document_id=document_id,
            soft_deleted_at__isnull=True,
        )
        .exclude(id=center_contact_id)
        .exists()
    )

    if duplicate_exists:
        raise DjangoValidationError(
            {
                "document_id": (
                    "Ya existe un contacto del centro con ese documento."
                )
            }
        )


def _apply_identity_fields(
    *,
    center_contact: Center_Contact,
    data: dict[str, Any],
) -> None:
    center_contact_type = _normalize_center_contact_type(
        _get_value(
            data=data,
            key="center_contact_type",
            current_value=center_contact.center_contact_type,
        )
    )

    first_name = _clean_string(
        _get_value(
            data=data,
            key="first_name",
            current_value=center_contact.first_name,
        )
    )
    last_name = _clean_string(
        _get_value(
            data=data,
            key="last_name",
            current_value=center_contact.last_name,
        )
    )
    institution_name = _clean_string(
        _get_value(
            data=data,
            key="institution_name",
            current_value=center_contact.institution_name,
        )
    )

    if center_contact_type == Choices_Center_Contact_Type.PERSON.value:
        if not first_name and not last_name:
            raise DjangoValidationError(
                {
                    "first_name": (
                        "Ingresa al menos el nombre o el apellido de la persona."
                    ),
                    "last_name": (
                        "Ingresa al menos el nombre o el apellido de la persona."
                    ),
                }
            )

        if "institution_name" in data and institution_name:
            raise DjangoValidationError(
                {
                    "institution_name": (
                        "institution_name no debe enviarse para un contacto "
                        "de tipo persona."
                    )
                }
            )

        center_contact.center_contact_type = center_contact_type
        center_contact.first_name = first_name
        center_contact.last_name = last_name
        center_contact.institution_name = ""
        return

    if center_contact_type == Choices_Center_Contact_Type.INSTITUTION.value:
        if not institution_name:
            raise DjangoValidationError(
                {
                    "institution_name": (
                        "El nombre de la institución es obligatorio."
                    )
                }
            )

        if ("first_name" in data and first_name) or (
            "last_name" in data and last_name
        ):
            raise DjangoValidationError(
                {
                    "first_name": (
                        "first_name no debe enviarse para un contacto "
                        "de tipo institución."
                    ),
                    "last_name": (
                        "last_name no debe enviarse para un contacto "
                        "de tipo institución."
                    ),
                }
            )

        center_contact.center_contact_type = center_contact_type
        center_contact.first_name = ""
        center_contact.last_name = ""
        center_contact.institution_name = institution_name
        return

    raise DjangoValidationError(
        {
            "center_contact_type": "Tipo de contacto inválido.",
        }
    )


def _apply_document_field(
    *,
    center_contact: Center_Contact,
    data: dict[str, Any],
) -> None:
    if "document_id" not in data:
        return

    center_contact.document_id = _normalize_document_id(data["document_id"])


def _apply_optional_text_field(
    *,
    center_contact: Center_Contact,
    data: dict[str, Any],
    payload_field_name: str,
    model_field_name: str | None = None,
) -> None:
    if payload_field_name not in data:
        return

    target_field_name = model_field_name or payload_field_name

    setattr(
        center_contact,
        target_field_name,
        _clean_string(data[payload_field_name]),
    )


def _apply_optional_email_field(
    *,
    center_contact: Center_Contact,
    data: dict[str, Any],
    payload_field_name: str,
    model_field_name: str | None = None,
) -> None:
    if payload_field_name not in data:
        return

    target_field_name = model_field_name or payload_field_name

    setattr(
        center_contact,
        target_field_name,
        _clean_email(data[payload_field_name]),
    )


def _apply_boolean_field(
    *,
    center_contact: Center_Contact,
    data: dict[str, Any],
    field_name: str,
) -> None:
    if field_name not in data:
        return

    setattr(center_contact, field_name, bool(data[field_name]))


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


def _build_center_contact_business_values(
    center_contact: Center_Contact,
) -> dict[str, Any]:
    return {
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
        "soft_deleted_at": _serialize_datetime(
            center_contact.soft_deleted_at
        ),
        "soft_deleted_by_id": center_contact.soft_deleted_by_id,
        "created_at": _serialize_datetime(
            getattr(center_contact, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(center_contact, "updated_at", None)
        ),
        "created_by_id": getattr(center_contact, "created_by_id", None),
        "updated_by_id": getattr(center_contact, "updated_by_id", None),
    }



def _create_center_contact_updated_audit_log(
    *,
    center_contact: Center_Contact,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=center_contact.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_CENTER_CONTACT_UPDATED,
        entity_type=AUDIT_ENTITY_TYPE_CENTER_CONTACT,
        entity_id=center_contact.id,
        reason=_clean_string(reason),
        old_values=old_values,
        new_values=new_values,
    )


@transaction.atomic
def update_center_contact(
    *,
    center_id: int,
    center_contact_id: int,
    data: dict[str, Any],
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
) -> Center_Contact:
    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=center_id,
    )

    center_exists = Veterinary_Center.objects.filter(
        id=center_id,
    ).exists()

    if not center_exists:
        raise VeterinaryCenterNotFoundError(
            f"Veterinary center with id {center_id} was not found."
        )

    try:
        center_contact = (
            Center_Contact.objects.select_for_update()
            .get(
                id=center_contact_id,
                veterinary_center_id=center_id,
                soft_deleted_at__isnull=True,
            )
        )
    except Center_Contact.DoesNotExist as exc:
        raise CenterContactNotFoundError(
            f"Center contact with id {center_contact_id} was not found."
        ) from exc

    old_values = _build_center_contact_audit_values(center_contact)
    old_business_values = _build_center_contact_business_values(
        center_contact
    )

    _apply_identity_fields(
        center_contact=center_contact,
        data=data,
    )

    _apply_document_field(
        center_contact=center_contact,
        data=data,
    )

    _validate_no_active_duplicate_document_id(
        center_id=center_id,
        center_contact_id=center_contact_id,
        document_id=center_contact.document_id,
    )

    _apply_optional_email_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="email",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="primary_phone",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="secondary_phone",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="tertiary_phone",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="address",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="city",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="region",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="country",
    )

    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="center_contact_notes",
        model_field_name="notes",
    )
    _apply_optional_text_field(
        center_contact=center_contact,
        data=data,
        payload_field_name="notes",
    )

    _apply_boolean_field(
        center_contact=center_contact,
        data=data,
        field_name="is_active",
    )

    new_business_values = _build_center_contact_business_values(
        center_contact
    )

    if old_business_values == new_business_values:
        return center_contact

    center_contact.full_clean()
    center_contact.save()

    new_values = _build_center_contact_audit_values(center_contact)

    _create_center_contact_updated_audit_log(
        center_contact=center_contact,
        actor=actor,
        member=member,
        reason=reason,
        old_values=old_values,
        new_values=new_values,
    )

    return center_contact


__all__ = [
    "update_center_contact",
]