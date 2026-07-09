# api/domains/pet/pedigree_policy.py

from __future__ import annotations

from api.domains.pet.errors import PetPedigreeRegistryRequiresPedigreeError


def validate_pet_pedigree_consistency_with_has_pedigree(
    *,
    has_pedigree: bool,
    pedigree_registry: str | None,
) -> None:
    """
    Enforces that pedigree_registry only has meaningful content when the pet has
    pedigree.
    """

    if has_pedigree:
        return

    if pedigree_registry is None:
        return

    if pedigree_registry.strip() == "":
        return

    raise PetPedigreeRegistryRequiresPedigreeError(
        "If has_pedigree is false, pedigree_registry must be null or empty."
    )


__all__ = [
    "validate_pet_pedigree_consistency_with_has_pedigree",
]