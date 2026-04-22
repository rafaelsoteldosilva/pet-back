# api/application/pet/commands/create_pet.py

from __future__ import annotations

"""
Application command: Create Pet.

Responsabilidad
---------------
Crear un nuevo paciente veterinario.

La capa application:
- coordina dominio e infraestructura
- usa ORM o repositories
- emite eventos si es necesario
"""

from datetime import date
from typing import Any, Optional

from django.db import transaction
from rest_framework.exceptions import ValidationError

from api.domain.pet.rules import (
    PetBreedDoesNotBelongToSpeciesError,
    PetRuleViolation,
    PetSpeciesNotAllowedForCenterError,
    validate_pet_species_and_breed_for_center,
)
from api.infrastructure.events.dispatcher import dispatch
from api.infrastructure.events.types import EVENT_CLINICAL_EVENT_OCCURRED
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.selectors.catalog import (
    get_allowed_species_ids_for_center,
    get_species_id_for_breed,
)


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


@transaction.atomic
def create_pet(
    *,
    veterinary_center_id: int,
    name: str,
    sex: str,
    species_id: int,
    breed_id: int | None = None,
    sterilized: bool = False,
    birth_date: date | None = None,
) -> Pet:
    """
    Crea un nuevo paciente veterinario.
    """

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
    except PetRuleViolation as exc:
        _raise_validation_error_for_rule_violation(exc)

    pet = Pet.objects.create(
        veterinary_center_id=veterinary_center_id,
        name=name,
        sex=sex,
        species_id=normalized_species_id,
        breed_id=normalized_breed_id,
        sterilized=sterilized,
        birth_date=birth_date,
    )

    dispatch(
        EVENT_CLINICAL_EVENT_OCCURRED,
        {
            "pet_id": pet.id,
            "event": "pet_created",
        },
    )

    return pet