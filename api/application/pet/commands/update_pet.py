# api/application/pet/commands/update_pet.py

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.catalog import (
    Breed_In_Center,
    Species_In_Center,
)
from api.infrastructure.orm.models.center import Center_Staff_Membership
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import (
    Choices_Pet_Status,
    Choices_Role,
)


PET_BASIC_DATA_UPDATE_ALLOWED_ROLES: set[str] = {
    Choices_Role.CENTER_ADMIN.value,
    Choices_Role.VETERINARIAN.value,
    Choices_Role.RECEPTIONIST.value,
}

AUDIT_ACTION_PET_UPDATED = "PET_UPDATED"
AUDIT_ENTITY_TYPE_PET = "Pet"


FIELD_ALIASES: dict[str, str] = {
    "species": "species_id",
    "breed": "breed_id",
    "last_attending_vet": "last_attending_vet_id",

    # Frontend / older naming compatibility
    "visual_identification_description": (
        "visual_identification_or_tattoo_description"
    ),
    "microchip_implanted_at": "microchip_date",
    "notes": "internal_notes",
}


WRITABLE_PET_FIELDS: set[str] = {
    "name",
    "sex",
    "species_id",
    "breed_id",
    "birth_date",
    "photo_url",
    "body_description",
    "size",
    "last_weight",
    "last_attending_vet_id",
    "reference",
    "sterilized",
    "has_pedigree",
    "pedigree_registry",
    "has_visual_identification",
    "visual_tag",
    "visual_identification_or_tattoo_description",
    "has_microchip",
    "microchip_code",
    "microchip_date",
    "microchip_body_region",
    "clinical_observations",
    "internal_notes",
    "status",
    "inactive_at",
    "deceased_at",
    "archived_at",
    "clinical_record_status",
}


NULLABLE_TEXT_FIELDS: set[str] = {
    "photo_url",
    "body_description",
    "size",
    "pedigree_registry",
    "visual_tag",
    "visual_identification_or_tattoo_description",
    "microchip_code",
    "microchip_body_region",
    "clinical_observations",
    "internal_notes",
}


BLANK_STRING_FIELDS: set[str] = {
    "reference",
}


FK_ID_FIELDS: set[str] = {
    "species_id",
    "breed_id",
    "last_attending_vet_id",
}


DECIMAL_FIELDS: set[str] = {
    "last_weight",
}


class PetNotFoundError(Exception):
    pass


def _model_has_field(
    model_or_instance: type[Any] | Any,
    field_name: str,
) -> bool:
    model = (
        model_or_instance
        if isinstance(model_or_instance, type)
        else type(model_or_instance)
    )

    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _model_can_set_field(
    model_or_instance: type[Any] | Any,
    field_name: str,
) -> bool:
    if _model_has_field(model_or_instance, field_name):
        return True

    if field_name.endswith("_id"):
        relation_field_name = field_name.removesuffix("_id")
        return _model_has_field(model_or_instance, relation_field_name)

    return False


def _is_blank(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == ""


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None

    if not isinstance(value, str):
        return str(value).strip() or None

    return value.strip() or None


def _clean_string(value: Any) -> str:
    return _clean_optional_string(value) or ""


def _normalize_write_data(data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for field_name, value in data.items():
        if field_name == "reason":
            continue

        normalized_field_name = FIELD_ALIASES.get(field_name, field_name)

        if normalized_field_name not in WRITABLE_PET_FIELDS:
            continue

        if not _model_can_set_field(Pet, normalized_field_name):
            continue

        if normalized_field_name in NULLABLE_TEXT_FIELDS:
            payload[normalized_field_name] = _clean_optional_string(value)
            continue

        if normalized_field_name in BLANK_STRING_FIELDS:
            payload[normalized_field_name] = (
                _clean_optional_string(value) or ""
            )
            continue

        if normalized_field_name in FK_ID_FIELDS:
            if value is None or _is_blank(value):
                payload[normalized_field_name] = None
            else:
                payload[normalized_field_name] = int(value)

            continue

        if normalized_field_name in DECIMAL_FIELDS:
            if value is None or _is_blank(value):
                payload[normalized_field_name] = None
            else:
                payload[normalized_field_name] = Decimal(str(value))

            continue

        payload[normalized_field_name] = value

    return payload


def _get_pet_or_raise(
    *,
    center_id: int,
    pet_id: int,
) -> Pet:
    filters: dict[str, Any] = {
        "id": pet_id,
        "veterinary_center_id": center_id,
    }

    if _model_has_field(Pet, "soft_deleted_at"):
        filters["soft_deleted_at__isnull"] = True

    try:
        return Pet.objects.select_for_update().get(**filters)
    except ObjectDoesNotExist as exc:
        raise PetNotFoundError(
            f"Pet with id {pet_id} was not found in center {center_id}."
        ) from exc


def _get_membership_role(membership: Center_Staff_Membership) -> str:
    role = getattr(membership, "role", "")

    return _clean_string(getattr(role, "value", role))


def _validate_actor_membership_for_center(
    *,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    center_id: int,
) -> None:
    if membership.veterinary_center_id != center_id:
        raise PermissionDenied(
            "La membresía activa no pertenece al centro veterinario indicado."
        )

    if membership.user_id != actor.id:
        raise PermissionDenied(
            "La membresía activa no pertenece al usuario autenticado."
        )

    if not membership.is_active:
        raise PermissionDenied(
            "La membresía del usuario en este centro no está activa."
        )

    if not membership.veterinary_center.is_active:
        raise PermissionDenied(
            "El centro veterinario no está activo."
        )


def _ensure_membership_can_update_pet_basic_data(
    *,
    membership: Center_Staff_Membership,
) -> None:
    role = _get_membership_role(membership)

    if role not in PET_BASIC_DATA_UPDATE_ALLOWED_ROLES:
        raise PermissionDenied(
            "No tienes permiso para editar datos del paciente."
        )


def get_allowed_species_ids_for_center(
    *,
    veterinary_center_id: int,
) -> set[int]:
    filters: dict[str, Any] = {
        "veterinary_center_id": veterinary_center_id,
    }

    if _model_has_field(Species_In_Center, "is_active"):
        filters["is_active"] = True

    if _model_has_field(Species_In_Center, "soft_deleted_at"):
        filters["soft_deleted_at__isnull"] = True

    return set(
        Species_In_Center.objects.filter(**filters).values_list(
            "id",
            flat=True,
        )
    )


def get_species_id_for_breed(
    breed_id: int,
) -> int | None:
    filters: dict[str, Any] = {
        "id": breed_id,
    }

    if _model_has_field(Breed_In_Center, "is_active"):
        filters["is_active"] = True

    if _model_has_field(Breed_In_Center, "soft_deleted_at"):
        filters["soft_deleted_at__isnull"] = True

    return (
        Breed_In_Center.objects.filter(**filters)
        .values_list(
            "species_in_center_id",
            flat=True,
        )
        .first()
    )


def _ensure_last_attending_vet_is_valid_for_center(
    *,
    center_id: int,
    last_attending_vet_id: int | None,
) -> None:
    if last_attending_vet_id is None:
        return

    filters: dict[str, Any] = {
        "id": last_attending_vet_id,
        "veterinary_center_id": center_id,
        "is_active": True,
        "role": Choices_Role.VETERINARIAN.value,
    }

    if _model_has_field(Center_Staff_Membership, "soft_deleted_at"):
        filters["soft_deleted_at__isnull"] = True

    if not Center_Staff_Membership.objects.filter(**filters).exists():
        raise DjangoValidationError(
            {
                "last_attending_vet_id": [
                    "El veterinario seleccionado no existe, no está activo, "
                    "no pertenece al centro o no tiene rol de veterinario."
                ]
            }
        )


def _clear_pet_relation_cache_if_needed(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> None:
    if "last_attending_vet_id" in payload:
        pet._state.fields_cache.pop("last_attending_vet", None)

    if "species_id" in payload:
        pet._state.fields_cache.pop("species", None)

    if "breed_id" in payload:
        pet._state.fields_cache.pop("breed", None)


def _resolve_species_and_breed_from_payload_or_pet(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> tuple[int | None, int | None]:
    species_id = payload.get("species_id", pet.species_id)
    breed_id = payload.get("breed_id", pet.breed_id)

    return species_id, breed_id


def _resolve_has_pedigree_and_registry_from_payload_or_pet(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> tuple[bool, str | None]:
    has_pedigree = bool(payload.get("has_pedigree", pet.has_pedigree))

    pedigree_registry = payload.get(
        "pedigree_registry",
        pet.pedigree_registry,
    )

    return has_pedigree, _clean_optional_string(pedigree_registry)


def _resolve_has_microchip_and_code_from_payload_or_pet(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> tuple[bool, str | None]:
    has_microchip = bool(payload.get("has_microchip", pet.has_microchip))

    microchip_code = payload.get(
        "microchip_code",
        pet.microchip_code,
    )

    return has_microchip, _clean_optional_string(microchip_code)


def _resolve_birth_date_and_microchip_date_from_payload_or_pet(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> tuple[date | None, date | None]:
    birth_date = payload.get("birth_date", pet.birth_date)
    microchip_date = payload.get("microchip_date", pet.microchip_date)

    return birth_date, microchip_date


def _ensure_species_change_does_not_leave_invalid_current_breed(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> None:
    if "species_id" not in payload:
        return

    if "breed_id" in payload:
        return

    if pet.breed_id is None:
        return

    new_species_id = payload["species_id"]

    if new_species_id is None:
        return

    current_breed_species_id = get_species_id_for_breed(pet.breed_id)

    if current_breed_species_id != new_species_id:
        raise DjangoValidationError(
            {
                "breed": [
                    "La raza actual no pertenece a la nueva especie seleccionada."
                ]
            }
        )


def validate_pet_species_and_breed_for_center(
    *,
    species_id: int | None,
    allowed_species_ids: set[int],
    breed_id: int | None,
    breed_species_id: int | None,
) -> None:
    errors: dict[str, list[str]] = {}

    if species_id is None:
        errors["species"] = ["La especie del paciente es obligatoria."]

    if allowed_species_ids and species_id not in allowed_species_ids:
        errors["species"] = [
            "La especie seleccionada no está habilitada para este centro."
        ]

    if breed_id is not None and breed_species_id is None:
        errors["breed"] = [
            "La raza seleccionada no existe o no está habilitada para este centro."
        ]

    if (
        species_id is not None
        and breed_id is not None
        and breed_species_id is not None
        and breed_species_id != species_id
    ):
        errors["breed"] = [
            "La raza seleccionada no pertenece a la especie seleccionada."
        ]

    if errors:
        raise DjangoValidationError(errors)


def validate_pet_pedigree_consistency_with_has_pedigree(
    *,
    has_pedigree: bool,
    pedigree_registry: str | None,
) -> None:
    if not has_pedigree and pedigree_registry:
        raise DjangoValidationError(
            {
                "pedigree_registry": [
                    "No puedes registrar pedigrí si el paciente no tiene pedigrí."
                ]
            }
        )


def validate_pet_microchip_consistency_with_has_microchip(
    *,
    has_microchip: bool,
    microchip_code: str | None,
    microchip_date: date | None,
) -> None:
    if has_microchip:
        return

    errors: dict[str, list[str]] = {}

    if microchip_code:
        errors["microchip_code"] = [
            "No puedes registrar un microchip si el paciente no tiene microchip."
        ]

    if microchip_date is not None:
        errors["microchip_date"] = [
            "No puedes registrar una fecha de microchip si el paciente no tiene microchip."
        ]

    if errors:
        raise DjangoValidationError(errors)


def validate_pet_microchip_date_not_before_birth_date(
    *,
    birth_date: date | None,
    microchip_date: date | None,
) -> None:
    if birth_date is None or microchip_date is None:
        return

    if microchip_date < birth_date:
        raise DjangoValidationError(
            {
                "microchip_date": [
                    "La fecha de implantación del microchip no puede ser anterior "
                    "a la fecha de nacimiento."
                ]
            }
        )


def _apply_status_timestamp_rules(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> None:
    if "status" not in payload:
        return

    new_status = payload["status"]

    if new_status == pet.status:
        return

    now = timezone.now()

    if new_status == Choices_Pet_Status.ACTIVE.value:
        payload["inactive_at"] = None
        payload["deceased_at"] = None
        payload["archived_at"] = None
        return

    if new_status == Choices_Pet_Status.INACTIVE.value:
        payload["inactive_at"] = now
        return

    if new_status == Choices_Pet_Status.DECEASED.value:
        payload["deceased_at"] = now
        return

    if new_status == Choices_Pet_Status.ARCHIVED.value:
        payload["archived_at"] = now
        return


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    return value


def _get_pet_value_for_audit(
    *,
    pet: Pet,
    field_name: str,
) -> Any:
    return _json_safe_value(getattr(pet, field_name, None))


def _build_pet_audit_snapshot(
    *,
    pet: Pet,
    field_names: set[str],
) -> dict[str, Any]:
    return {
        field_name: _get_pet_value_for_audit(
            pet=pet,
            field_name=field_name,
        )
        for field_name in sorted(field_names)
    }


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


def _build_changed_values(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    changed_fields = [
        field_name
        for field_name in sorted(after.keys())
        if before.get(field_name) != after.get(field_name)
    ]

    old_values = {
        field_name: before.get(field_name)
        for field_name in changed_fields
    }

    new_values = {
        field_name: after.get(field_name)
        for field_name in changed_fields
    }

    return old_values, new_values


def _create_pet_update_audit_log(
    *,
    pet: Pet,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    reason: str | None,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> None:
    if not old_values and not new_values:
        return

    Audit_Log.objects.create(
        veterinary_center_id=pet.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_membership_role(membership),
        action=AUDIT_ACTION_PET_UPDATED,
        entity_type=AUDIT_ENTITY_TYPE_PET,
        entity_id=pet.id,
        reason=_clean_string(reason),
        old_values=old_values,
        new_values=new_values,
    )


@transaction.atomic
def update_pet(
    *,
    center_id: int,
    pet_id: int,
    data: dict[str, Any],
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    reason: str | None,
) -> Pet:
    _validate_actor_membership_for_center(
        actor=actor,
        membership=membership,
        center_id=center_id,
    )

    _ensure_membership_can_update_pet_basic_data(
        membership=membership,
    )

    pet = _get_pet_or_raise(
        center_id=center_id,
        pet_id=pet_id,
    )

    payload = _normalize_write_data(data)

    if not payload:
        return pet

    if "last_attending_vet_id" in payload:
        _ensure_last_attending_vet_is_valid_for_center(
            center_id=center_id,
            last_attending_vet_id=payload["last_attending_vet_id"],
        )

    _apply_status_timestamp_rules(
        pet=pet,
        payload=payload,
    )

    _ensure_species_change_does_not_leave_invalid_current_breed(
        pet=pet,
        payload=payload,
    )

    species_id_for_validation, breed_id_for_validation = (
        _resolve_species_and_breed_from_payload_or_pet(
            pet=pet,
            payload=payload,
        )
    )

    has_pedigree_for_validation, pedigree_registry_for_validation = (
        _resolve_has_pedigree_and_registry_from_payload_or_pet(
            pet=pet,
            payload=payload,
        )
    )

    has_microchip_for_validation, microchip_code_for_validation = (
        _resolve_has_microchip_and_code_from_payload_or_pet(
            pet=pet,
            payload=payload,
        )
    )

    birth_date_for_validation, microchip_date_for_validation = (
        _resolve_birth_date_and_microchip_date_from_payload_or_pet(
            pet=pet,
            payload=payload,
        )
    )

    allowed_species_ids = get_allowed_species_ids_for_center(
        veterinary_center_id=center_id,
    )

    breed_species_id = None

    if breed_id_for_validation is not None:
        breed_species_id = get_species_id_for_breed(breed_id_for_validation)

    validate_pet_species_and_breed_for_center(
        species_id=species_id_for_validation,
        allowed_species_ids=allowed_species_ids,
        breed_id=breed_id_for_validation,
        breed_species_id=breed_species_id,
    )

    validate_pet_pedigree_consistency_with_has_pedigree(
        has_pedigree=has_pedigree_for_validation,
        pedigree_registry=pedigree_registry_for_validation,
    )

    validate_pet_microchip_consistency_with_has_microchip(
        has_microchip=has_microchip_for_validation,
        microchip_code=microchip_code_for_validation,
        microchip_date=microchip_date_for_validation,
    )

    validate_pet_microchip_date_not_before_birth_date(
        birth_date=birth_date_for_validation,
        microchip_date=microchip_date_for_validation,
    )

    update_fields = set(payload.keys())

    before = _build_pet_audit_snapshot(
        pet=pet,
        field_names=update_fields,
    )

    for field_name, value in payload.items():
        setattr(pet, field_name, value)

    after = _build_pet_audit_snapshot(
        pet=pet,
        field_names=update_fields,
    )

    old_values, new_values = _build_changed_values(
        before=before,
        after=after,
    )

    if not old_values and not new_values:
        return pet

    if _model_has_field(pet, "updated_at"):
        update_fields.add("updated_at")

    try:
        pet.save(update_fields=sorted(update_fields))
    except DjangoValidationError as exc:
        raise exc

    _clear_pet_relation_cache_if_needed(
        pet=pet,
        payload=payload,
    )

    _create_pet_update_audit_log(
        pet=pet,
        actor=actor,
        membership=membership,
        reason=reason,
        old_values=old_values,
        new_values=new_values,
    )
    
    return pet


__all__ = [
    "PetNotFoundError",
    "update_pet",
]