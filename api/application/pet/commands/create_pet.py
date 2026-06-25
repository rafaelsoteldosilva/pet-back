# api/application/pet/commands/create_pet.py

"""
Application command: Create Pet.

Responsabilidad
---------------
Crear un nuevo paciente veterinario.

La capa application:
- coordina dominio e infraestructura
- usa ORM o repositories
- emite eventos si es necesario
- registra auditoría de acciones importantes
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from api.domains.pet.errors import (
    PetBreedDoesNotBelongToSpeciesError,
    PetRuleViolationError,
    PetSpeciesNotAllowedForCenterError,
)
from api.domains.pet.rules import (
    validate_pet_species_and_breed_for_center,
)
from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import Center_Staff_Membership
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.models.user import Pet_Control_User
from api.infrastructure.orm.selectors.catalog import (
    get_allowed_species_ids_for_center,
    get_species_id_for_breed,
)

AUDIT_ACTION_PET_CREATED = "PET_CREATED"
AUDIT_ENTITY_TYPE_PET = "Pet"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _serialize_date(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _extract_int_id(
    field_name: str,
    value: Any,
    *,
    required: bool,
) -> int | None:
    if value in (None, ""):
        if required:
            raise ValidationError({field_name: ["This field is required."]})

        return None

    if hasattr(value, "id"):
        value = value.id

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {
                field_name: ["A valid integer is required."],
            }
        ) from exc


def _coerce_required_int(field_name: str, value: Any) -> int:
    coerced = _extract_int_id(
        field_name,
        value,
        required=True,
    )

    if coerced is None:
        raise ValidationError({field_name: ["This field is required."]})

    return coerced


def _coerce_optional_int(field_name: str, value: Any) -> int | None:
    return _extract_int_id(
        field_name,
        value,
        required=False,
    )


def _raise_validation_error_for_rule_violation(
    exc: PetRuleViolationError,
) -> None:
    if isinstance(exc, PetSpeciesNotAllowedForCenterError):
        raise ValidationError(
            {
                "species_id": [
                    "This species is not enabled for this veterinary center.",
                ]
            }
        ) from exc

    if isinstance(exc, PetBreedDoesNotBelongToSpeciesError):
        raise ValidationError(
            {
                "breed_id": [
                    "The selected breed does not belong to the selected species.",
                ]
            }
        ) from exc

    raise ValidationError({"detail": [str(exc)]}) from exc


def _raise_validation_error_from_django_error(
    exc: DjangoValidationError,
) -> None:
    """
    Converts Django model validation errors into DRF validation errors.

    This keeps the application command compatible with API endpoints that expect
    rest_framework.exceptions.ValidationError.
    """

    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict) from exc

    raise ValidationError({"detail": exc.messages}) from exc


def _validate_actor_membership_for_center(
    *,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    center_id: int,
) -> None:
    if membership.veterinary_center_id != center_id:
        raise PermissionError(
            "La membresía activa no pertenece al centro veterinario indicado."
        )

    if membership.user_id != actor.id:
        raise PermissionError(
            "La membresía activa no pertenece al usuario autenticado."
        )

    if not membership.is_active:
        raise PermissionError(
            "La membresía del usuario en este centro no está activa."
        )

    if not membership.veterinary_center.is_active:
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


def _get_membership_role(membership: Center_Staff_Membership) -> str:
    role = getattr(membership, "role", "")

    return _clean_string(getattr(role, "value", role))


def _build_pet_audit_values(pet: Pet) -> dict[str, Any]:
    return {
        "id": pet.id,
        "veterinary_center_id": pet.veterinary_center_id,
        "history_code": getattr(pet, "history_code", ""),
        "name": pet.name,
        "sex": pet.sex,
        "species_id": pet.species_id,
        "breed_id": pet.breed_id,
        "sterilized": pet.sterilized,
        "birth_date": _serialize_date(pet.birth_date),
        "status": getattr(pet, "status", ""),
        "clinical_record_status": getattr(
            pet,
            "clinical_record_status",
            "",
        ),
        "is_active": getattr(pet, "is_active", True),
        "created_at": _serialize_datetime(
            getattr(pet, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(pet, "updated_at", None)
        ),
        "soft_deleted_at": _serialize_datetime(
            getattr(pet, "soft_deleted_at", None)
        ),
        "soft_deleted_by_id": getattr(pet, "soft_deleted_by_id", None),
    }


def _create_pet_created_audit_log(
    *,
    pet: Pet,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    reason: str | None,
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=pet.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_membership_role(membership),
        action=AUDIT_ACTION_PET_CREATED,
        entity_type=AUDIT_ENTITY_TYPE_PET,
        entity_id=pet.id,
        reason=_clean_string(reason),
        old_values={},
        new_values=_build_pet_audit_values(pet),
    )


@transaction.atomic
def create_pet(
    *,
    veterinary_center_id: int,
    name: str,
    sex: str,
    species_id: int,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    breed_id: int | None = None,
    sterilized: bool = False,
    birth_date: date | None = None,
    reason: str | None = None,
) -> Pet:
    """
    Crea un nuevo paciente veterinario.
    """

    _validate_actor_membership_for_center(
        actor=actor,
        membership=membership,
        center_id=veterinary_center_id,
    )

    normalized_species_id = _coerce_required_int("species_id", species_id)
    normalized_breed_id = _coerce_optional_int("breed_id", breed_id)

    allowed_species_ids = get_allowed_species_ids_for_center(
        veterinary_center_id=veterinary_center_id,
    )

    breed_species_id = None

    if normalized_breed_id is not None:
        breed_species_id = get_species_id_for_breed(normalized_breed_id)

    try:
        validate_pet_species_and_breed_for_center(
            veterinary_center_id=veterinary_center_id,
            species_id=normalized_species_id,
            allowed_species_ids=allowed_species_ids,
            breed_id=normalized_breed_id,
            breed_species_id=breed_species_id,
        )
    except PetRuleViolationError as exc:
        _raise_validation_error_for_rule_violation(exc)

    pet = Pet(
        veterinary_center_id=veterinary_center_id,
        name=name,
        sex=sex,
        species_id=normalized_species_id,
        breed_id=normalized_breed_id,
        sterilized=sterilized,
        birth_date=birth_date,
    )

    try:
        pet.assign_history_code_if_missing()
        pet.save()
    except DjangoValidationError as exc:
        _raise_validation_error_from_django_error(exc)

    _create_pet_created_audit_log(
        pet=pet,
        actor=actor,
        membership=membership,
        reason=reason,
    )

    return pet


__all__ = [
    "create_pet",
]