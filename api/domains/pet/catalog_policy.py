# api/domains/pet/catalog_policy.py

from __future__ import annotations

from collections.abc import Iterable

from api.domains.pet.errors import (
    PetBreedDoesNotBelongToSpeciesError,
    PetSpeciesNotAllowedForCenterError,
)


def _normalize_ids(values: Iterable[int]) -> set[int]:
    return {int(value) for value in values}


def ensure_pet_species_is_allowed_for_center(
    *,
    veterinary_center_id: int,
    species_id: int,
    allowed_species_ids: Iterable[int],
) -> None:
    """
    Enforces that the selected species belongs to the subset of species enabled
    for the veterinary center.

    Important:
    An empty allowed_species_ids collection means the center has no species
    restriction configured.
    """

    allowed_species_id_set = _normalize_ids(allowed_species_ids)

    if not allowed_species_id_set:
        return

    if int(species_id) not in allowed_species_id_set:
        raise PetSpeciesNotAllowedForCenterError(
            species_id=int(species_id),
            veterinary_center_id=int(veterinary_center_id),
        )


def ensure_pet_breed_belongs_to_species(
    *,
    species_id: int,
    breed_id: int | None,
    breed_species_id: int | None,
) -> None:
    """
    Enforces that the selected breed belongs to the selected species.

    If breed_id is None, the rule does nothing.
    """

    if breed_id is None:
        return

    if breed_species_id is None or int(breed_species_id) != int(species_id):
        raise PetBreedDoesNotBelongToSpeciesError(
            breed_id=int(breed_id),
            species_id=int(species_id),
        )


def validate_pet_species_and_breed_for_center(
    *,
    veterinary_center_id: int,
    species_id: int,
    allowed_species_ids: Iterable[int],
    breed_id: int | None,
    breed_species_id: int | None,
) -> None:
    """
    Main orchestration rule for pet catalog validation.

    Rules enforced:
    - the pet species must be allowed for the veterinary center
    - the pet breed, if present, must belong to the selected species
    """

    ensure_pet_species_is_allowed_for_center(
        veterinary_center_id=veterinary_center_id,
        species_id=species_id,
        allowed_species_ids=allowed_species_ids,
    )

    ensure_pet_breed_belongs_to_species(
        species_id=species_id,
        breed_id=breed_id,
        breed_species_id=breed_species_id,
    )


__all__ = [
    "ensure_pet_species_is_allowed_for_center",
    "ensure_pet_breed_belongs_to_species",
    "validate_pet_species_and_breed_for_center",
]