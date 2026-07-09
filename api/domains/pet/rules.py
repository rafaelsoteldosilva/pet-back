# api/domains/pet/rules.py

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from api.domains.pet.errors import (
    PetCannotBeDeletedBecauseClinicalRecordsExistError,
    PetCannotBeDeletedByDifferentUserError,
    PetContactLinkCenterContactDifferentCenterError,
    PetContactLinkCenterContactInvalidTypeError,
    PetBreedDoesNotBelongToSpeciesError,
    PetContactLinkBillingResponsibleRequiresBillingPermissionError,
    PetContactLinkInvalidRoleForInstitutionError,
    PetContactLinkInvalidRoleForPersonError,
    PetMicrochipCode15DigitsNotApplicableError,
    PetMicrochipCodeRequiresMicrochipCodeError,
    PetMicrochipDateBeforeBirthDateError,
    PetPedigreeRegistryRequiresPedigreeError,
    PetSpeciesNotAllowedForCenterError,
)
from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Pet_Contact_Link_Role,
)


# ======================================================
# Shared helpers
# ======================================================


def _normalize_ids(values: Iterable[int]) -> set[int]:
    return {int(value) for value in values}


def _normalize_choice_code(value: str | None) -> str:
    return str(value or "").strip().upper()


def _normalize_strings(values: Iterable[str]) -> set[str]:
    return {
        str(value).strip()
        for value in values
        if str(value).strip()
    }


# ======================================================
# Species / breed rules
# ======================================================


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


# ======================================================
# Pet deletion rules
# ======================================================


def ensure_pet_can_be_deleted(
    *,
    clinical_record_sources: Iterable[str],
    actor_user_id: int,
    pet_created_by_user_id: int | None,
) -> None:
    """
    Enforces whether a Pet can be deleted.

    Domain rules:
    - A pet can be deleted only when it has no clinical records.
    - A pet can be deleted only by the same user who created it.

    This function receives already-calculated facts from the application layer.
    It must not import Django ORM models and must not query the database.
    """

    normalized_sources = sorted(
        _normalize_strings(clinical_record_sources)
    )

    if normalized_sources:
        raise PetCannotBeDeletedBecauseClinicalRecordsExistError(
            clinical_record_sources=normalized_sources,
        )

    if pet_created_by_user_id is None:
        raise PetCannotBeDeletedByDifferentUserError()

    if int(actor_user_id) != int(pet_created_by_user_id):
        raise PetCannotBeDeletedByDifferentUserError()

# ======================================================
# Pedigree rules
# ======================================================


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


# ======================================================
# Microchip rules
# ======================================================


def validate_pet_microchip_code_consistency_with_has_microchip(
    *,
    has_microchip: bool,
    microchip_code: str | None,
) -> None:
    """
    Enforces that microchip_code only has meaningful content when the pet has a
    microchip.
    """

    if has_microchip:
        return

    if microchip_code is None:
        return

    if microchip_code.strip() == "":
        return

    raise PetMicrochipCodeRequiresMicrochipCodeError(
        "If has_microchip is false, microchip_code must be null or empty."
    )


def validate_pet_microchip_code_15_digits_consistency_with_has_microchip(
    *,
    has_microchip: bool,
    microchip_code_is_15_digits: bool | None,
) -> None:
    """
    Enforces consistency between has_microchip and microchip_code_is_15_digits.

    Rules enforced:
    - If microchip_code_is_15_digits is None, the rule does nothing.
      This means ISO 11784 compliance is unknown or not applicable.
    - If microchip_code_is_15_digits is True or False, then the pet must have a
      microchip.
    """

    if microchip_code_is_15_digits is None:
        return

    if has_microchip:
        return

    raise PetMicrochipCode15DigitsNotApplicableError(
        "If microchip_code_is_15_digits is true or false, "
        "has_microchip must be true."
    )


def validate_pet_microchip_date_not_before_birth_date(
    *,
    birth_date: date | None,
    microchip_date: date | None,
) -> None:
    """
    Enforces that the microchip implantation date cannot be before the pet's
    birth date.

    If either date is missing, the rule does nothing.
    """

    if birth_date is None:
        return

    if microchip_date is None:
        return

    if microchip_date < birth_date:
        raise PetMicrochipDateBeforeBirthDateError(
            "microchip_date cannot be before birth_date."
        )


# ======================================================
# Pet_Contact_Link rules
# ======================================================


def ensure_center_contact_belongs_to_pet_center(
    *,
    pet_center_id: int | None,
    center_contact_center_id: int | None,
) -> None:
    """
    Enforces that a Pet_Contact_Link can only be created when the pet and the
    Center_Contact record belong to the same veterinary center.
    """

    if pet_center_id is None or center_contact_center_id is None:
        return

    if int(pet_center_id) != int(center_contact_center_id):
        raise PetContactLinkCenterContactDifferentCenterError()


def ensure_pet_contact_link_role_matches_center_contact_type(
    *,
    center_contact_type: str | None,
    role: str | None,
) -> None:
    """
    Enforces that person Center_Contact records receive only
    person-compatible Pet_Contact_Link roles, and institution
    Center_Contact records receive only institution-compatible
    Pet_Contact_Link roles.
    """

    normalized_center_contact_type = _normalize_choice_code(
        center_contact_type
    )
    normalized_role = _normalize_choice_code(role)

    if not normalized_center_contact_type or not normalized_role:
        return

    if (
        normalized_center_contact_type
        == Choices_Center_Contact_Type.PERSON.value
    ):
        if not Choices_Pet_Contact_Link_Role.is_person_role(normalized_role):
            raise PetContactLinkInvalidRoleForPersonError()

        return

    if (
        normalized_center_contact_type
        == Choices_Center_Contact_Type.INSTITUTION.value
    ):
        if not Choices_Pet_Contact_Link_Role.is_institution_role(
            normalized_role
        ):
            raise PetContactLinkInvalidRoleForInstitutionError()

        return

    raise PetContactLinkCenterContactInvalidTypeError()


def ensure_pet_contact_link_permission_consistency(
    *,
    role: str | None,
    is_active: bool,
    can_receive_billing: bool,
) -> None:
    """
    Enforces Pet_Contact_Link role/permission consistency rules.

    Current rule:
    - An active billing responsible link must be able to receive billing
      information.

    OWNER_GUARDIAN is intentionally not forced to be primary. The main contact
    is controlled by is_primary_contact, independently from the role.
    """

    if not is_active:
        return

    normalized_role = _normalize_choice_code(role)

    if (
        normalized_role
        == Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value
    ):
        if not can_receive_billing:
            raise PetContactLinkBillingResponsibleRequiresBillingPermissionError()


def validate_pet_contact_link_consistency(
    *,
    pet_center_id: int | None,
    center_contact_center_id: int | None,
    center_contact_type: str | None,
    role: str | None,
    is_active: bool,
    can_receive_billing: bool,
) -> None:
    """
    Main orchestration rule for Pet_Contact_Link validation.

    Rules enforced:
    - the Center_Contact record must belong to the same veterinary center
      as the pet
    - the selected Pet_Contact_Link role must be compatible with the
      Center_Contact type
    - active billing responsible links must be able to receive billing info
    """

    ensure_center_contact_belongs_to_pet_center(
        pet_center_id=pet_center_id,
        center_contact_center_id=center_contact_center_id,
    )

    ensure_pet_contact_link_role_matches_center_contact_type(
        center_contact_type=center_contact_type,
        role=role,
    )

    ensure_pet_contact_link_permission_consistency(
        role=role,
        is_active=is_active,
        can_receive_billing=can_receive_billing,
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