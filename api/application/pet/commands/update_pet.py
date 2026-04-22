# api/application/pet/commands/update_pet.py

from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from api.domain.pet.rules import (
    PetBreedDoesNotBelongToSpeciesError,
    PetRuleViolation,
    PetSpeciesNotAllowedForCenterError,
    validate_pet_species_and_breed_for_center,
)
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.selectors.catalog import (
    get_allowed_species_ids_for_center,
    get_species_id_for_breed,
)

ALLOWED_FIELDS = {
    "name",
    "species_id",
    "breed_id",
    "sex",
    "sterilized",
    "birth_date",
    "body_description",
    "size",
    "last_weight",
}


def _extract_int_id(
    field_name: str,
    value: Any,
    *,
    required: bool,
) -> Optional[int]:
    if value in (None, ""):
        if required:
            raise ValidationError({field_name: ["This field is required."]})
        return None

    if hasattr(value, "id"):
        value = value.id

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({field_name: ["A valid integer is required."]}) from exc


def _coerce_required_int(field_name: str, value: Any) -> int:
    coerced = _extract_int_id(field_name, value, required=True)
    if coerced is None:
        raise ValidationError({field_name: ["This field is required."]})
    return coerced


def _coerce_optional_int(field_name: str, value: Any) -> Optional[int]:
    return _extract_int_id(field_name, value, required=False)


def _normalize_write_data(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)

    payload.pop("id", None)
    payload.pop("veterinary_center", None)
    payload.pop("veterinary_center_id", None)

    if "species" in payload and "species_id" not in payload:
        payload["species_id"] = payload["species"]
    payload.pop("species", None)

    if "breed" in payload and "breed_id" not in payload:
        payload["breed_id"] = payload["breed"]
    payload.pop("breed", None)

    for field_name in payload.keys():
        if field_name not in ALLOWED_FIELDS:
            raise ValueError(f"Field '{field_name}' cannot be updated")

    if "species_id" in payload:
        payload["species_id"] = _coerce_required_int(
            "species_id",
            payload["species_id"],
        )

    if "breed_id" in payload:
        payload["breed_id"] = _coerce_optional_int(
            "breed_id",
            payload["breed_id"],
        )

    return payload


def _raise_validation_error_for_rule_violation(exc: PetRuleViolation) -> None:
    if isinstance(exc, PetSpeciesNotAllowedForCenterError):
        raise ValidationError(
            {"species_id": ["This species is not enabled for this veterinary center."]}
        ) from exc

    if isinstance(exc, PetBreedDoesNotBelongToSpeciesError):
        raise ValidationError(
            {"breed_id": ["The selected breed does not belong to the selected species."]}
        ) from exc

    raise ValidationError({"detail": [str(exc)]}) from exc


def _get_pet_or_raise(*, center_id: int, pet_id: int) -> Pet:
    try:
        return Pet.objects.select_for_update().get(
            id=pet_id,
            veterinary_center_id=center_id,
        )
    except Pet.DoesNotExist as exc:
        raise NotFound("Pet not found.") from exc


def _resolve_species_and_breed_from_payload_or_pet(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> tuple[int, Optional[int]]:
    """
    Resolves the species_id and breed_id that must be validated for this update.

    Rule:
    - if the payload provides a value, use it
    - otherwise, use the current value from the pet
    """
    if "species_id" in payload:
        species_id = _coerce_required_int("species_id", payload["species_id"])
    else:
        species_id = int(pet.species_id)

    if "breed_id" in payload:
        breed_id = _coerce_optional_int("breed_id", payload["breed_id"])
    elif pet.breed_id is None:
        breed_id = None
    else:
        breed_id = int(pet.breed_id)

    return species_id, breed_id


def _ensure_species_change_does_not_leave_invalid_current_breed(
    *,
    pet: Pet,
    payload: dict[str, Any],
) -> None:
    """
    If species is changed but breed is omitted from the payload, do not silently
    keep a current breed that belongs to another species.
    """
    if "species_id" not in payload or "breed_id" in payload:
        return

    current_breed_id = pet.breed_id
    if current_breed_id is None:
        return

    new_species_id = int(payload["species_id"])
    current_breed_species_id = get_species_id_for_breed(int(current_breed_id))

    if current_breed_species_id is None or int(current_breed_species_id) != new_species_id:
        raise ValidationError(
            {
                "breed_id": [
                    "The current breed does not belong to the selected species. "
                    "Send breed_id=null to clear it or send a breed_id that belongs "
                    "to the selected species."
                ]
            }
        )


@transaction.atomic
def update_pet(
    *,
    center_id: int,
    pet_id: int,
    data: Dict[str, Any],
) -> Pet:
    pet = _get_pet_or_raise(
        center_id=center_id,
        pet_id=pet_id,
    )
    payload = _normalize_write_data(data)

    if not payload:
        return pet

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

    allowed_species_ids = get_allowed_species_ids_for_center(
        veterinary_center_id=center_id,
    )

    breed_species_id = None
    if breed_id_for_validation is not None:
        breed_species_id = get_species_id_for_breed(breed_id_for_validation)

    try:
        validate_pet_species_and_breed_for_center(
            veterinary_center_id=center_id,
            species_id=species_id_for_validation,
            allowed_species_ids=allowed_species_ids,
            breed_id=breed_id_for_validation,
            breed_species_id=breed_species_id,
        )
        
    except PetRuleViolation as exc:
        _raise_validation_error_for_rule_violation(exc)


    for field_name, value in payload.items():
        setattr(pet, field_name, value)

    pet.save(update_fields=list(payload.keys()))
    
    return pet