# api/domains/pet/services.py

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Final, Mapping

from api.shared.choices.choices import Choices_Pet_Contact_Link_Role


@dataclass(frozen=True)
class PetContactDefaultPermissions:
    is_primary_contact: bool
    is_emergency_contact: bool
    can_authorize_treatment: bool
    can_receive_medical_updates: bool
    can_receive_billing: bool
    can_pickup_pet: bool


_NO_PERMISSIONS: Final[PetContactDefaultPermissions] = PetContactDefaultPermissions(
    is_primary_contact=False,
    is_emergency_contact=False,
    can_authorize_treatment=False,
    can_receive_medical_updates=False,
    can_receive_billing=False,
    can_pickup_pet=False,
)


_DEFAULT_PERMISSIONS_BY_ROLE: Final[dict[str, PetContactDefaultPermissions]] = {
    Choices_Pet_Contact_Link_Role.OWNER_GUARDIAN.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=True,
            can_receive_medical_updates=True,
            can_receive_billing=True,
            can_pickup_pet=True,
        )
    ),
    Choices_Pet_Contact_Link_Role.CAREGIVER.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=False,
            can_receive_medical_updates=True,
            can_receive_billing=False,
            can_pickup_pet=True,
        )
    ),
    Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=False,
            can_receive_medical_updates=False,
            can_receive_billing=True,
            can_pickup_pet=False,
        )
    ),
    Choices_Pet_Contact_Link_Role.REFERRING_VET.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=False,
            can_receive_medical_updates=True,
            can_receive_billing=False,
            can_pickup_pet=False,
        )
    ),
    Choices_Pet_Contact_Link_Role.RESPONSIBLE_INSTITUTION.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=True,
            can_receive_medical_updates=True,
            can_receive_billing=True,
            can_pickup_pet=False,
        )
    ),
    Choices_Pet_Contact_Link_Role.REFERRING_INSTITUTION.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=False,
            can_receive_medical_updates=True,
            can_receive_billing=False,
            can_pickup_pet=False,
        )
    ),
    Choices_Pet_Contact_Link_Role.BREEDER.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=False,
            can_receive_medical_updates=True,
            can_receive_billing=False,
            can_pickup_pet=False,
        )
    ),
    Choices_Pet_Contact_Link_Role.SHELTER_OR_FOUNDATION.value: (
        PetContactDefaultPermissions(
            is_primary_contact=False,
            is_emergency_contact=False,
            can_authorize_treatment=False,
            can_receive_medical_updates=True,
            can_receive_billing=False,
            can_pickup_pet=False,
        )
    ),
}


def _normalize_role(role: str | None) -> str:
    return str(role or "").strip().upper()


def get_default_pet_contact_permissions(
    role: str,
) -> PetContactDefaultPermissions:
    normalized_role = _normalize_role(role)

    return _DEFAULT_PERMISSIONS_BY_ROLE.get(
        normalized_role,
        _NO_PERMISSIONS,
    )


def get_pet_contact_permission_field_names() -> tuple[str, ...]:
    return tuple(field.name for field in fields(PetContactDefaultPermissions))


def build_pet_contact_permission_data(
    *,
    role: str,
    overrides: Mapping[str, bool] | None = None,
) -> dict[str, bool]:
    normalized_role = _normalize_role(role)

    permission_data = asdict(
        get_default_pet_contact_permissions(normalized_role)
    )

    if overrides:
        for field_name in permission_data:
            if field_name in overrides:
                permission_data[field_name] = overrides[field_name]

    if normalized_role == Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value:
        permission_data["can_receive_billing"] = True

    return permission_data


__all__ = [
    "PetContactDefaultPermissions",
    "get_default_pet_contact_permissions",
    "get_pet_contact_permission_field_names",
    "build_pet_contact_permission_data",
]