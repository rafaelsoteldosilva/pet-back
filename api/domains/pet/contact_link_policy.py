# api/domains/pet/contact_link_policy.py

from __future__ import annotations

from api.domains.pet.errors import (
    PetContactLinkBillingResponsibleRequiresBillingPermissionError,
    PetContactLinkCenterContactDifferentCenterError,
    PetContactLinkCenterContactInvalidTypeError,
    PetContactLinkInvalidRoleForInstitutionError,
    PetContactLinkInvalidRoleForPersonError,
)
from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Pet_Contact_Link_Role,
)


def _normalize_choice_code(value: str | None) -> str:
    return str(value or "").strip().upper()


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
    "ensure_center_contact_belongs_to_pet_center",
    "ensure_pet_contact_link_role_matches_center_contact_type",
    "ensure_pet_contact_link_permission_consistency",
    "validate_pet_contact_link_consistency",
]