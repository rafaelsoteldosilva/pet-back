# api/application/pet/commands/delete_pet_draft.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import Center_Staff_Membership
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import (
    Choices_Pet_Clinical_Record_Status,
    Choices_Role,
)


DRAFT_PET_DELETE_ALLOWED_ROLES: set[str] = {
    Choices_Role.CENTER_ADMIN.value,
    Choices_Role.VETERINARIAN.value,
    Choices_Role.RECEPTIONIST.value,
}

AUDIT_ACTION_PET_DRAFT_DELETED = "PET_DRAFT_DELETED"
AUDIT_ENTITY_TYPE_PET = "Pet"
DEFAULT_DELETE_PET_DRAFT_REASON = "Eliminación de paciente en borrador."


class PetNotFoundError(Exception):
    pass


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


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


def _ensure_membership_can_delete_pet_draft(
    *,
    membership: Center_Staff_Membership,
) -> None:
    actor_role = _get_membership_role(membership)

    if actor_role not in DRAFT_PET_DELETE_ALLOWED_ROLES:
        raise PermissionDenied(
            "No tienes permiso para eliminar pacientes en borrador."
        )


def _get_pet_draft_or_raise(
    *,
    center_id: int,
    pet_id: int,
) -> Pet:
    """
    Locks only the Pet row.

    Do not add select_related() here together with select_for_update().
    Some related fields are nullable, and PostgreSQL can fail with:
    FOR UPDATE cannot be applied to the nullable side of an outer join.
    """

    try:
        return (
            Pet.objects.select_for_update()
            .get(
                id=pet_id,
                veterinary_center_id=center_id,
            )
        )
    except Pet.DoesNotExist as exc:
        raise PetNotFoundError(
            f"Pet with id {pet_id} was not found in center {center_id}."
        ) from exc


def _ensure_pet_is_draft(
    *,
    pet: Pet,
) -> None:
    if (
        pet.clinical_record_status
        == Choices_Pet_Clinical_Record_Status.DRAFT.value
    ):
        return

    raise DjangoValidationError(
        {
            "clinical_record_status": [
                "Solo se pueden eliminar pacientes en borrador."
            ]
        }
    )


def _build_pet_old_values(
    *,
    pet: Pet,
) -> dict[str, Any]:
    return {
        "id": pet.id,
        "history_code": pet.history_code,
        "name": pet.name,
        "sex": pet.sex,
        "species_id": pet.species_id,
        "breed_id": pet.breed_id,
        "sterilized": pet.sterilized,
        "birth_date": pet.birth_date.isoformat() if pet.birth_date else None,
        "body_description": pet.body_description,
        "size": pet.size,
        "last_weight": str(pet.last_weight)
        if pet.last_weight is not None
        else None,
        "last_attending_vet_id": pet.last_attending_vet_id,
        "last_attending_vet_external_name": (
            pet.last_attending_vet_external_name
        ),
        "reference": pet.reference,
        "has_pedigree": pet.has_pedigree,
        "pedigree_registry": pet.pedigree_registry,
        "visual_tag": pet.visual_tag,
        "visual_identification_or_tattoo_description": (
            pet.visual_identification_or_tattoo_description
        ),
        "has_microchip": pet.has_microchip,
        "microchip_code": pet.microchip_code,
        "microchip_date": (
            pet.microchip_date.isoformat()
            if pet.microchip_date
            else None
        ),
        "microchip_body_region": pet.microchip_body_region,
        "clinical_observations": pet.clinical_observations,
        "internal_notes": pet.internal_notes,
        "photo_url": pet.photo_url,
        "status": pet.status,
        "clinical_record_status": pet.clinical_record_status,
        "veterinary_center_id": pet.veterinary_center_id,
        "created_at": pet.created_at.isoformat() if pet.created_at else None,
        "updated_at": pet.updated_at.isoformat() if pet.updated_at else None,
    }


def delete_pet_draft(
    *,
    center_id: int,
    pet_id: int,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    reason: str | None = None,
) -> None:
    """
    Deletes a pet only when its clinical record is still DRAFT.

    This command performs a hard delete because a draft patient should not yet
    be part of the permanent clinical record.
    """

    with transaction.atomic():
        _validate_actor_membership_for_center(
            actor=actor,
            membership=membership,
            center_id=center_id,
        )

        _ensure_membership_can_delete_pet_draft(
            membership=membership,
        )

        pet = _get_pet_draft_or_raise(
            center_id=center_id,
            pet_id=pet_id,
        )

        _ensure_pet_is_draft(
            pet=pet,
        )

        old_values = _build_pet_old_values(
            pet=pet,
        )

        actor_role = _get_membership_role(membership)

        audit_reason = (
            _clean_string(reason) or DEFAULT_DELETE_PET_DRAFT_REASON
        )

        pet.delete()

        Audit_Log.objects.create(
            veterinary_center_id=center_id,
            actor_user=actor,
            actor_role=actor_role,
            action=AUDIT_ACTION_PET_DRAFT_DELETED,
            entity_type=AUDIT_ENTITY_TYPE_PET,
            entity_id=pet_id,
            reason=audit_reason,
            old_values=old_values,
            new_values={},
            metadata={
                "deleted_as_draft": True,
                "delete_type": "hard_delete",
            },
        )


__all__ = [
    "delete_pet_draft",
    "PetNotFoundError",
]