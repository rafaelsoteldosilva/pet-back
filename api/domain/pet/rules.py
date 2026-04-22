from __future__ import annotations

from typing import Iterable, Optional, Set


class PetRuleViolation(Exception):
    """
    Base exception for pet domain rule violations.
    """


class PetSpeciesNotAllowedForCenterError(PetRuleViolation):
    """
    Raised when the selected species is not enabled for the veterinary center.
    """

    def __init__(self, species_id: int, veterinary_center_id: int):
        self.species_id = int(species_id)
        self.veterinary_center_id = int(veterinary_center_id)
        super().__init__(
            f"Species {self.species_id} is not allowed for veterinary center "
            f"{self.veterinary_center_id}."
        )


class PetBreedDoesNotBelongToSpeciesError(PetRuleViolation):
    """
    Raised when the selected breed does not belong to the selected species.
    """

    def __init__(self, breed_id: int, species_id: int):
        self.breed_id = int(breed_id)
        self.species_id = int(species_id)
        super().__init__(
            f"Breed {self.breed_id} does not belong to species {self.species_id}."
        )


def _normalize_ids(values: Iterable[int]) -> Set[int]:
    return {int(value) for value in values}


def ensure_pet_species_is_allowed_for_center(
    *,
    veterinary_center_id: int,
    species_id: int,
    allowed_species_ids: Iterable[int],
) -> None:
    """
    Enforces that the selected species belongs to the subset of species
    enabled for the veterinary center.
    """
    allowed_species_id_set = _normalize_ids(allowed_species_ids)

    if int(species_id) not in allowed_species_id_set:
        
        raise PetSpeciesNotAllowedForCenterError(
            species_id=int(species_id),
            veterinary_center_id=int(veterinary_center_id),
        )


def ensure_pet_breed_belongs_to_species(
    *,
    species_id: int,
    breed_id: Optional[int],
    breed_species_id: Optional[int],
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
    breed_id: Optional[int],
    breed_species_id: Optional[int],
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
    