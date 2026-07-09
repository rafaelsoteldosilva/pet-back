# api/domains/pet/rules.py

from __future__ import annotations

from api.domains.pet.catalog_policy import (
    ensure_pet_breed_belongs_to_species,
    ensure_pet_species_is_allowed_for_center,
    validate_pet_species_and_breed_for_center,
)
from api.domains.pet.contact_link_policy import (
    ensure_center_contact_belongs_to_pet_center,
    ensure_pet_contact_link_permission_consistency,
    ensure_pet_contact_link_role_matches_center_contact_type,
    validate_pet_contact_link_consistency,
)
from api.domains.pet.deletion_policy import ensure_pet_can_be_deleted
from api.domains.pet.microchip_policy import (
    validate_pet_microchip_code_15_digits_consistency_with_has_microchip,
    validate_pet_microchip_code_consistency_with_has_microchip,
    validate_pet_microchip_date_not_before_birth_date,
)
from api.domains.pet.pedigree_policy import (
    validate_pet_pedigree_consistency_with_has_pedigree,
)


__all__ = [
    "ensure_pet_species_is_allowed_for_center",
    "ensure_pet_breed_belongs_to_species",
    "validate_pet_species_and_breed_for_center",
    "ensure_pet_can_be_deleted",
    "validate_pet_pedigree_consistency_with_has_pedigree",
    "validate_pet_microchip_code_consistency_with_has_microchip",
    "validate_pet_microchip_code_15_digits_consistency_with_has_microchip",
    "validate_pet_microchip_date_not_before_birth_date",
    "ensure_center_contact_belongs_to_pet_center",
    "ensure_pet_contact_link_role_matches_center_contact_type",
    "ensure_pet_contact_link_permission_consistency",
    "validate_pet_contact_link_consistency",
]