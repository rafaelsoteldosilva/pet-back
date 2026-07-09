# api/application/pet/commands/delete_pet_contact_link.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import Center_Staff_Member
from api.infrastructure.orm.models.pet import Pet_Contact_Link
from api.infrastructure.orm.models.user import Pet_Control_User

AUDIT_ACTION_PET_CONTACT_LINK_SOFT_DELETED = (
    "PET_CONTACT_LINK_SOFT_DELETED"
)
AUDIT_ENTITY_TYPE_PET_CONTACT_LINK = "Pet_Contact_Link"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _validate_actor_member_for_center(
    *,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    center_id: int,
) -> None:
    if member.veterinary_center_id != center_id:
        raise PermissionError(
            "La membresía activa no pertenece al centro veterinario indicado."
        )

    if member.user_id != actor.id:
        raise PermissionError(
            "La membresía activa no pertenece al usuario autenticado."
        )

    if not member.is_active:
        raise PermissionError(
            "La membresía del usuario en este centro no está activa."
        )

    if not member.veterinary_center.is_active:
        raise PermissionError(
            "El centro veterinario no está activo."
        )


def _get_actor_display_name(actor: Pet_Control_User) -> str:
    get_full_name = getattr(actor, "get_full_name", None)

    if callable(get_full_name):
        full_name = _clean_string(get_full_name())

        if full_name:
            return full_name

    get_username = getattr(actor, "get_username", None)

    if callable(get_username):
        username = _clean_string(get_username())

        if username:
            return username

    email = _clean_string(getattr(actor, "email", ""))

    if email:
        return email

    return f"User {actor.id}"


def _get_member_role(member: Center_Staff_Member) -> str:
    role = getattr(member, "role", "")

    return _clean_string(getattr(role, "value", role))


def _build_pet_contact_link_audit_values(
    pet_contact_link: Pet_Contact_Link,
) -> dict[str, Any]:
    return {
        "id": pet_contact_link.id,
        "pet_id": pet_contact_link.pet_id,
        "veterinary_center_id": pet_contact_link.pet.veterinary_center_id,
        "center_contact_id": pet_contact_link.center_contact_id,
        "role": pet_contact_link.role,
        "specific_relationship": pet_contact_link.specific_relationship,
        "notes": pet_contact_link.notes,
        "is_primary_contact": pet_contact_link.is_primary_contact,
        "is_emergency_contact": pet_contact_link.is_emergency_contact,
        "can_authorize_treatment": (
            pet_contact_link.can_authorize_treatment
        ),
        "can_receive_medical_updates": (
            pet_contact_link.can_receive_medical_updates
        ),
        "can_receive_billing": pet_contact_link.can_receive_billing,
        "can_pickup_pet": pet_contact_link.can_pickup_pet,
        "is_active": pet_contact_link.is_active,
        "created_by_id": getattr(pet_contact_link, "created_by_id", None),
        "soft_deleted_at": _serialize_datetime(
            getattr(pet_contact_link, "soft_deleted_at", None)
        ),
        "soft_deleted_by_id": getattr(
            pet_contact_link,
            "soft_deleted_by_id",
            None,
        ),
        "created_at": _serialize_datetime(
            getattr(pet_contact_link, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(pet_contact_link, "updated_at", None)
        ),
    }


def _create_pet_contact_link_soft_deleted_audit_log(
    *,
    pet_contact_link: Pet_Contact_Link,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=pet_contact_link.pet.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_PET_CONTACT_LINK_SOFT_DELETED,
        entity_type=AUDIT_ENTITY_TYPE_PET_CONTACT_LINK,
        entity_id=pet_contact_link.id,
        reason=_clean_string(reason),
        old_values=old_values,
        new_values=new_values,
    )


@transaction.atomic
def delete_pet_contact_link_from_pet(
    *,
    center_id: int,
    pet_id: int,
    pet_contact_link_id: int,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
) -> None:
    """
    Soft deletes the pet-contact link for the given pet.

    Important:
    This removes only the Pet_Contact_Link from normal use, not the
    Center_Contact record itself. The Center_Contact record can
    still be reused elsewhere.
    """

    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=center_id,
    )

    try:
        pet_contact_link = (
            Pet_Contact_Link.objects.select_for_update()
            .select_related(
                "pet",
                "center_contact",
            )
            .get(
                id=pet_contact_link_id,
                pet_id=pet_id,
                pet__veterinary_center_id=center_id,
            )
        )
    except Pet_Contact_Link.DoesNotExist as exc:
        raise ValidationError(
            {
                "pet_contact_link_id": (
                    "El vínculo de contacto asociado al paciente no existe "
                    "o no pertenece al centro indicado."
                )
            }
        ) from exc

    if pet_contact_link.soft_deleted_at is not None:
        return

    old_values = _build_pet_contact_link_audit_values(pet_contact_link)

    pet_contact_link.is_active = False
    pet_contact_link.soft_deleted_at = timezone.now()
    pet_contact_link.soft_deleted_by = member

    pet_contact_link.full_clean()
    pet_contact_link.save(
        update_fields=[
            "is_active",
            "soft_deleted_at",
            "soft_deleted_by",
            "updated_at",
        ]
    )

    new_values = _build_pet_contact_link_audit_values(pet_contact_link)

    _create_pet_contact_link_soft_deleted_audit_log(
        pet_contact_link=pet_contact_link,
        actor=actor,
        member=member,
        reason=reason,
        old_values=old_values,
        new_values=new_values,
    )


__all__ = [
    "delete_pet_contact_link_from_pet",
]