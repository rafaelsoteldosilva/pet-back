# api/application/pet/commands/update_pet_contact_link.py

from __future__ import annotations

from typing import Any, Mapping

from django.core.exceptions import (
    FieldDoesNotExist,
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from django.db.models import Model
from rest_framework.exceptions import ValidationError as DRFValidationError

from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import (
    Center_Contact,
    Center_Staff_Member,
)
from api.infrastructure.orm.models.pet import Pet, Pet_Contact_Link
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Pet_Contact_Link_Role,
)
from api.shared.utils.normalize_document_id import (
    is_valid_chilean_rut,
    normalize_document_id,
)


class PetContactLinkNotFoundError(Exception):
    """Raised when the Pet_Contact_Link does not exist for the given pet/center."""


CENTER_CONTACT_FIELD_MAP: dict[str, str] = {
    "center_contact_type": "center_contact_type",
    "first_name": "first_name",
    "last_name": "last_name",
    "institution_name": "institution_name",
    "country": "country",
    "document_id": "document_id",
    "email": "email",
    "primary_phone": "primary_phone",
    "secondary_phone": "secondary_phone",
    "tertiary_phone": "tertiary_phone",
    "address": "address",
    "city": "city",
    "region": "region",
    "center_contact_notes": "notes",
}


PET_CONTACT_LINK_FIELD_MAP: dict[str, str] = {
    "role": "role",
    "specific_relationship": "specific_relationship",
    "is_primary_contact": "is_primary_contact",
    "is_emergency_contact": "is_emergency_contact",
    "can_authorize_treatment": "can_authorize_treatment",
    "can_receive_medical_updates": "can_receive_medical_updates",
    "can_receive_billing": "can_receive_billing",
    "can_pickup_pet": "can_pickup_pet",
    "pet_contact_link_notes": "notes",
}


CENTER_CONTACT_MODEL_TO_API_FIELD_MAP: dict[str, str] = {
    "center_contact_type": "center_contact_type",
    "first_name": "first_name",
    "last_name": "last_name",
    "institution_name": "institution_name",
    "country": "country",
    "document_id": "document_id",
    "email": "email",
    "primary_phone": "primary_phone",
    "secondary_phone": "secondary_phone",
    "tertiary_phone": "tertiary_phone",
    "address": "address",
    "city": "city",
    "region": "region",
    "notes": "center_contact_notes",
}


PET_CONTACT_LINK_MODEL_TO_API_FIELD_MAP: dict[str, str] = {
    "role": "role",
    "specific_relationship": "specific_relationship",
    "is_primary_contact": "is_primary_contact",
    "is_emergency_contact": "is_emergency_contact",
    "can_authorize_treatment": "can_authorize_treatment",
    "can_receive_medical_updates": "can_receive_medical_updates",
    "can_receive_billing": "can_receive_billing",
    "can_pickup_pet": "can_pickup_pet",
    "notes": "pet_contact_link_notes",
    "center_contact": "center_contact",
}


AUDIT_ACTION_PET_CONTACT_LINK_UPDATED = "PET_CONTACT_LINK_UPDATED"
AUDIT_ENTITY_TYPE_PET_CONTACT_LINK = "Pet_Contact_Link"


def _map_validation_error_fields(
    error_dict: dict[str, list[Any]],
    field_map: dict[str, str],
) -> dict[str, list[Any]]:
    mapped_errors: dict[str, list[Any]] = {}

    for field_name, messages in error_dict.items():
        api_field_name = field_map.get(field_name, field_name)
        mapped_errors[api_field_name] = messages

    return mapped_errors


def _raise_validation_error_from_django_error(
    exc: DjangoValidationError,
    *,
    field_map: dict[str, str] | None = None,
) -> None:
    if hasattr(exc, "message_dict"):
        message_dict = exc.message_dict

        if field_map:
            message_dict = _map_validation_error_fields(
                message_dict,
                field_map,
            )

        raise DRFValidationError(message_dict) from exc

    raise DRFValidationError({"detail": exc.messages}) from exc


def _raise_invalid_document_id() -> None:
    raise DRFValidationError(
        {
            "document_id": [
                "El documento indicado no es un RUT chileno válido."
            ]
        }
    )


def _model_has_field(instance: Model, field_name: str) -> bool:
    try:
        instance._meta.get_field(field_name)
    except FieldDoesNotExist:
        return False

    return True


def _clean_blank_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _clean_email(value: Any) -> str:
    return _clean_blank_string(value).lower()


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _validate_document_id_for_database(document_id: str) -> None:
    """
    Empty document_id is allowed in this flow.

    But when document_id has a value, it must be a valid Chilean RUT/RUN.
    The actual verifier-digit formula lives in is_valid_chilean_rut().
    """

    if not document_id:
        return

    if not is_valid_chilean_rut(document_id):
        _raise_invalid_document_id()


def _normalize_document_id(value: Any) -> str:
    document_id = _clean_blank_string(value)

    if not document_id:
        return ""

    normalized_document_id = normalize_document_id(document_id)

    if not normalized_document_id:
        _raise_invalid_document_id()

    _validate_document_id_for_database(normalized_document_id)

    return normalized_document_id


def _normalize_center_contact_document_id_before_save(
    center_contact: Center_Contact,
) -> bool:
    """
    Final safety check before saving Center_Contact through this command.

    Returns True when document_id was normalized and therefore must be included
    in update_fields.
    """

    current_document_id = _clean_blank_string(
        getattr(center_contact, "document_id", "")
    )

    if not current_document_id:
        return False

    normalized_document_id = normalize_document_id(current_document_id)

    if not normalized_document_id:
        _raise_invalid_document_id()

    _validate_document_id_for_database(normalized_document_id)

    if normalized_document_id == current_document_id:
        return False

    center_contact.document_id = normalized_document_id
    return True


def _save_model(
    instance: Model,
    *,
    update_fields: set[str],
    field_map: dict[str, str] | None = None,
) -> None:
    if not update_fields:
        return

    if isinstance(instance, Center_Contact):
        document_id_was_normalized = (
            _normalize_center_contact_document_id_before_save(instance)
        )

        if document_id_was_normalized:
            update_fields.add("document_id")

    if _model_has_field(instance, "updated_at"):
        update_fields.add("updated_at")

    try:
        instance.save(update_fields=sorted(update_fields))
    except DjangoValidationError as exc:
        _raise_validation_error_from_django_error(
            exc,
            field_map=field_map,
        )


def _set_model_value(
    instance: Model,
    field_name: str,
    value: Any,
    update_fields: set[str],
) -> None:
    if not _model_has_field(instance, field_name):
        raise DRFValidationError(
            {
                field_name: [
                    f"El campo '{field_name}' no existe en el modelo correspondiente."
                ]
            }
        )

    current_value = getattr(instance, field_name)

    if current_value == value:
        return

    setattr(instance, field_name, value)
    update_fields.add(field_name)


def _normalize_choice_code(value: Any) -> str:
    return _clean_blank_string(value).upper()


def _normalize_update_data(data: Mapping[str, Any]) -> dict[str, Any]:
    normalized_data = dict(data)

    blank_string_fields = {
        "first_name",
        "last_name",
        "institution_name",
        "primary_phone",
        "secondary_phone",
        "tertiary_phone",
        "city",
        "region",
        "country",
        "address",
        "center_contact_notes",
        "specific_relationship",
        "pet_contact_link_notes",
    }

    for field_name in blank_string_fields:
        if field_name in normalized_data:
            normalized_data[field_name] = _clean_blank_string(
                normalized_data[field_name]
            )

    if "email" in normalized_data:
        normalized_data["email"] = _clean_email(normalized_data["email"])

    if "document_id" in normalized_data:
        normalized_data["document_id"] = _normalize_document_id(
            normalized_data["document_id"]
        )

    if "center_contact_type" in normalized_data:
        normalized_data["center_contact_type"] = _normalize_choice_code(
            normalized_data["center_contact_type"]
        )

    if "role" in normalized_data:
        normalized_data["role"] = _normalize_choice_code(
            normalized_data["role"]
        )

    return normalized_data


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
        full_name = _clean_blank_string(get_full_name())

        if full_name:
            return full_name

    get_username = getattr(actor, "get_username", None)

    if callable(get_username):
        username = _clean_blank_string(get_username())

        if username:
            return username

    email = _clean_blank_string(getattr(actor, "email", ""))

    if email:
        return email

    return f"User {actor.id}"


def _get_member_role(member: Center_Staff_Member) -> str:
    role = getattr(member, "role", "")

    return _clean_blank_string(getattr(role, "value", role))


def _validate_unique_document_id_for_center(
    *,
    center_contact: Center_Contact,
    center_id: int,
    document_id: str,
) -> None:
    clean_document_id = _clean_blank_string(document_id)

    if not clean_document_id:
        return

    duplicate_exists = (
        Center_Contact.objects.filter(
            veterinary_center_id=center_id,
            document_id=clean_document_id,
            soft_deleted_at__isnull=True,
        )
        .exclude(pk=center_contact.pk)
        .exists()
    )

    if duplicate_exists:
        raise DRFValidationError(
            {
                "document_id": [
                    "Ya existe otro contacto activo del centro con este RUT / identificación."
                ]
            }
        )


def _validate_single_active_primary_contact(
    *,
    pet_contact_link: Pet_Contact_Link,
    pet_id: int,
    wants_primary_contact: bool,
) -> None:
    if not wants_primary_contact:
        return

    another_primary_exists = (
        Pet_Contact_Link.objects.select_for_update()
        .filter(
            pet_id=pet_id,
            is_active=True,
            is_primary_contact=True,
        )
        .exclude(pk=pet_contact_link.pk)
        .exists()
    )

    if another_primary_exists:
        raise DRFValidationError(
            {
                "is_primary_contact": [
                    "Este paciente ya tiene otro contacto principal activo."
                ]
            }
        )


def _validate_role_exists(role: str) -> None:
    allowed_values = {choice.value for choice in Choices_Pet_Contact_Link_Role}

    if role not in allowed_values:
        raise DRFValidationError(
            {
                "role": [
                    f"Rol de contacto inválido: {role}.",
                ]
            }
        )


def _validate_role_matches_center_contact_type(
    *,
    role: str,
    center_contact_type: str,
) -> None:
    if center_contact_type == Choices_Center_Contact_Type.PERSON.value:
        if not Choices_Pet_Contact_Link_Role.is_person_role(role):
            raise DRFValidationError(
                {
                    "role": [
                        "Para un contacto de tipo persona, selecciona un rol "
                        "válido para personas."
                    ]
                }
            )

        return

    if center_contact_type == Choices_Center_Contact_Type.INSTITUTION.value:
        if not Choices_Pet_Contact_Link_Role.is_institution_role(role):
            raise DRFValidationError(
                {
                    "role": [
                        "Para un contacto de tipo institución, selecciona un rol "
                        "válido para instituciones."
                    ]
                }
            )

        return

    raise DRFValidationError(
        {
            "center_contact_type": [
                "Tipo de contacto inválido.",
            ]
        }
    )


def _validate_center_contact_is_active(
    center_contact: Center_Contact,
) -> None:
    if center_contact.is_active:
        return

    raise DRFValidationError(
        {
            "center_contact": [
                "El contacto del centro está inactivo y no puede modificarse "
                "desde este vínculo."
            ]
        }
    )


def _get_pet_contact_link_for_update(
    *,
    center_id: int,
    pet_id: int,
    pet_contact_link_id: int,
) -> Pet_Contact_Link:
    try:
        return (
            Pet_Contact_Link.objects.select_for_update()
            .select_related(
                "pet",
                "center_contact",
                "pet__veterinary_center",
            )
            .get(
                id=pet_contact_link_id,
                pet_id=pet_id,
                pet__veterinary_center_id=center_id,
                is_active=True,
            )
        )
    except Pet_Contact_Link.DoesNotExist as exc:
        raise PetContactLinkNotFoundError(
            "No se encontró el vínculo de contacto activo para este paciente."
        ) from exc


def _apply_center_contact_type_consistency(
    *,
    center_contact: Center_Contact,
    center_contact_update_fields: set[str],
) -> None:
    if (
        center_contact.center_contact_type
        == Choices_Center_Contact_Type.PERSON.value
    ):
        _set_model_value(
            center_contact,
            "institution_name",
            "",
            center_contact_update_fields,
        )

        return

    if (
        center_contact.center_contact_type
        == Choices_Center_Contact_Type.INSTITUTION.value
    ):
        _set_model_value(
            center_contact,
            "first_name",
            "",
            center_contact_update_fields,
        )
        _set_model_value(
            center_contact,
            "last_name",
            "",
            center_contact_update_fields,
        )

        return

    raise DRFValidationError(
        {
            "center_contact_type": [
                "Tipo de contacto inválido.",
            ]
        }
    )


def _force_billing_permission_for_billing_role(
    *,
    pet_contact_link: Pet_Contact_Link,
    pet_contact_link_update_fields: set[str],
) -> None:
    if (
        pet_contact_link.role
        != Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value
    ):
        return

    _set_model_value(
        pet_contact_link,
        "can_receive_billing",
        True,
        pet_contact_link_update_fields,
    )


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
            getattr(center_contact, "soft_deleted_at", None)
        ),
        "soft_deleted_by_id": getattr(
            center_contact,
            "soft_deleted_by_id",
            None,
        ),
        "created_at": _serialize_datetime(
            getattr(center_contact, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(center_contact, "updated_at", None)
        ),
    }


def _build_pet_contact_link_audit_values(
    pet_contact_link: Pet_Contact_Link,
) -> dict[str, Any]:
    return {
        "id": pet_contact_link.id,
        "pet_id": pet_contact_link.pet_id,
        "veterinary_center_id": pet_contact_link.pet.veterinary_center_id,
        "center_contact_id": pet_contact_link.center_contact_id,
        "role": pet_contact_link.role,
        "specific_relationship": pet_contact_link.specific_relationship,
        "notes": pet_contact_link.notes,
        "is_primary_contact": pet_contact_link.is_primary_contact,
        "is_emergency_contact": pet_contact_link.is_emergency_contact,
        "can_authorize_treatment": (
            pet_contact_link.can_authorize_treatment
        ),
        "can_receive_medical_updates": (
            pet_contact_link.can_receive_medical_updates
        ),
        "can_receive_billing": pet_contact_link.can_receive_billing,
        "can_pickup_pet": pet_contact_link.can_pickup_pet,
        "is_active": pet_contact_link.is_active,
        "created_by_id": getattr(pet_contact_link, "created_by_id", None),
        "soft_deleted_at": _serialize_datetime(
            getattr(pet_contact_link, "soft_deleted_at", None)
        ),
        "soft_deleted_by_id": getattr(
            pet_contact_link,
            "soft_deleted_by_id",
            None,
        ),
        "created_at": _serialize_datetime(
            getattr(pet_contact_link, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(pet_contact_link, "updated_at", None)
        ),
    }


def _build_combined_audit_values(
    *,
    pet_contact_link: Pet_Contact_Link,
    center_contact: Center_Contact,
) -> dict[str, Any]:
    return {
        "pet_contact_link": _build_pet_contact_link_audit_values(
            pet_contact_link
        ),
        "center_contact": _build_center_contact_audit_values(
            center_contact
        ),
    }


def _create_pet_contact_link_updated_audit_log(
    *,
    pet_contact_link: Pet_Contact_Link,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=pet_contact_link.pet.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_PET_CONTACT_LINK_UPDATED,
        entity_type=AUDIT_ENTITY_TYPE_PET_CONTACT_LINK,
        entity_id=pet_contact_link.id,
        reason=_clean_blank_string(reason),
        old_values=old_values,
        new_values=new_values,
    )


@transaction.atomic
def update_pet_contact_link(
    *,
    center_id: int,
    pet_id: int,
    pet_contact_link_id: int,
    data: Mapping[str, Any],
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
) -> Pet_Contact_Link:
    """
    Updates both:
    - Center_Contact data: identity, document ID, phones, email, address, notes.
    - Pet_Contact_Link data: role, permissions, specific relationship, notes.
    """

    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=center_id,
    )

    clean_data = {
        key: value
        for key, value in data.items()
        if key != "reason"
    }

    normalized_data = _normalize_update_data(clean_data)

    pet_contact_link = _get_pet_contact_link_for_update(
        center_id=center_id,
        pet_id=pet_id,
        pet_contact_link_id=pet_contact_link_id,
    )

    pet: Pet = pet_contact_link.pet
    center_contact: Center_Contact = pet_contact_link.center_contact

    _validate_center_contact_is_active(center_contact)

    old_values = _build_combined_audit_values(
        pet_contact_link=pet_contact_link,
        center_contact=center_contact,
    )

    center_contact_update_fields: set[str] = set()
    pet_contact_link_update_fields: set[str] = set()

    for api_field_name, model_field_name in CENTER_CONTACT_FIELD_MAP.items():
        if api_field_name in normalized_data:
            _set_model_value(
                center_contact,
                model_field_name,
                normalized_data[api_field_name],
                center_contact_update_fields,
            )

    _apply_center_contact_type_consistency(
        center_contact=center_contact,
        center_contact_update_fields=center_contact_update_fields,
    )

    for api_field_name, model_field_name in PET_CONTACT_LINK_FIELD_MAP.items():
        if api_field_name in normalized_data:
            _set_model_value(
                pet_contact_link,
                model_field_name,
                normalized_data[api_field_name],
                pet_contact_link_update_fields,
            )

    _validate_role_exists(pet_contact_link.role)

    _validate_role_matches_center_contact_type(
        role=pet_contact_link.role,
        center_contact_type=center_contact.center_contact_type,
    )

    _force_billing_permission_for_billing_role(
        pet_contact_link=pet_contact_link,
        pet_contact_link_update_fields=pet_contact_link_update_fields,
    )

    if center_contact_update_fields:
        effective_document_id = _clean_blank_string(
            getattr(center_contact, "document_id", "")
        )

        _validate_unique_document_id_for_center(
            center_contact=center_contact,
            center_id=center_id,
            document_id=effective_document_id,
        )

        _save_model(
            center_contact,
            update_fields=center_contact_update_fields,
            field_map=CENTER_CONTACT_MODEL_TO_API_FIELD_MAP,
        )

    if pet_contact_link_update_fields:
        _validate_single_active_primary_contact(
            pet_contact_link=pet_contact_link,
            pet_id=pet.id,
            wants_primary_contact=bool(
                getattr(pet_contact_link, "is_primary_contact", False)
            ),
        )

        _save_model(
            pet_contact_link,
            update_fields=pet_contact_link_update_fields,
            field_map=PET_CONTACT_LINK_MODEL_TO_API_FIELD_MAP,
        )

    if not center_contact_update_fields and not pet_contact_link_update_fields:
        return pet_contact_link

    new_values = _build_combined_audit_values(
        pet_contact_link=pet_contact_link,
        center_contact=center_contact,
    )

    _create_pet_contact_link_updated_audit_log(
        pet_contact_link=pet_contact_link,
        actor=actor,
        member=member,
        reason=reason,
        old_values=old_values,
        new_values=new_values,
    )

    return pet_contact_link


__all__ = [
    "PetContactLinkNotFoundError",
    "update_pet_contact_link",
]