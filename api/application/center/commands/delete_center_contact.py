# api/application/center/commands/delete_center_contact.py

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from api.application.center.errors import (
    CenterContactHasPetContactLinksError,
    CenterContactNotFoundError,
    VeterinaryCenterNotFoundError,
)
from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import (
    Center_Contact,
    Center_Staff_Member,
    Veterinary_Center,
)
from api.infrastructure.orm.models.pet import Pet_Contact_Link
from api.infrastructure.orm.models.user import Pet_Control_User

AUDIT_ACTION_CENTER_CONTACT_SOFT_DELETED = "CENTER_CONTACT_SOFT_DELETED"
AUDIT_ENTITY_TYPE_CENTER_CONTACT = "Center_Contact"


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


def _build_center_contact_audit_values(
    contact: Center_Contact,
) -> dict[str, Any]:
    return {
        "id": contact.id,
        "veterinary_center_id": contact.veterinary_center_id,
        "center_contact_type": contact.center_contact_type,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "institution_name": contact.institution_name,
        "document_id": contact.document_id,
        "email": contact.email,
        "primary_phone": contact.primary_phone,
        "secondary_phone": contact.secondary_phone,
        "tertiary_phone": contact.tertiary_phone,
        "address": contact.address,
        "city": contact.city,
        "region": contact.region,
        "country": contact.country,
        "notes": contact.notes,
        "is_active": contact.is_active,
        "soft_deleted_at": _serialize_datetime(contact.soft_deleted_at),
        "soft_deleted_by_id": contact.soft_deleted_by_id,
    }


def _create_center_contact_soft_deleted_audit_log(
    *,
    contact: Center_Contact,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=contact.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_CENTER_CONTACT_SOFT_DELETED,
        entity_type=AUDIT_ENTITY_TYPE_CENTER_CONTACT,
        entity_id=contact.id,
        reason=_clean_string(reason),
        old_values=old_values,
        new_values=new_values,
    )


@transaction.atomic
def delete_center_contact(
    *,
    center_id: int,
    center_contact_id: int,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
) -> None:
    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=center_id,
    )

    center_exists = Veterinary_Center.objects.filter(
        id=center_id,
    ).exists()

    if not center_exists:
        raise VeterinaryCenterNotFoundError(
            f"Veterinary center with id {center_id} was not found."
        )

    contact = (
        Center_Contact.objects.select_for_update()
        .filter(
            id=center_contact_id,
            veterinary_center_id=center_id,
        )
        .first()
    )

    if contact is None:
        raise CenterContactNotFoundError(
            "Center contact with id "
            f"{center_contact_id} was not found for center {center_id}."
        )

    if contact.soft_deleted_at is not None:
        return

    linked_pet_links = Pet_Contact_Link.objects.filter(
        center_contact_id=center_contact_id,
        pet__veterinary_center_id=center_id,
        is_active=True,
    )

    total_linked_pets = (
        linked_pet_links.values("pet_id")
        .distinct()
        .count()
    )

    if total_linked_pets > 0:
        first_three_pet_rows = (
            linked_pet_links.order_by(
                "pet__name",
                "pet_id",
            )
            .values_list(
                "pet_id",
                "pet__name",
            )
            .distinct()[:3]
        )

        first_three_pet_names = [
            str(pet_name).strip() or f"Mascota #{pet_id}"
            for pet_id, pet_name in first_three_pet_rows
        ]

        raise CenterContactHasPetContactLinksError(
            pet_names=first_three_pet_names,
            total_linked_pets=total_linked_pets,
        )

    old_values = _build_center_contact_audit_values(contact)

    contact.is_active = False
    contact.soft_deleted_at = timezone.now()
    contact.soft_deleted_by = actor

    contact.full_clean()
    contact.save(
        update_fields=[
            "is_active",
            "soft_deleted_at",
            "soft_deleted_by",
            "updated_at",
        ]
    )

    new_values = _build_center_contact_audit_values(contact)

    _create_center_contact_soft_deleted_audit_log(
        contact=contact,
        actor=actor,
        member=member,
        reason=reason,
        old_values=old_values,
        new_values=new_values,
    )


__all__ = [
    "delete_center_contact",
]