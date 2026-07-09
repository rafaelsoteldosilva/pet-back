# api/application/pet/commands/add_pet_contact_link.py

from __future__ import annotations

from typing import Any, Final

from django.core.exceptions import ValidationError
from django.db import transaction

from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import (
    Center_Contact,
    Center_Staff_Member,
)
from api.infrastructure.orm.models.pet import Pet, Pet_Contact_Link
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Pet_Contact_Link_Role,
)

pet_contact_link_permission_data = dict[str, bool]

DEFAULT_PET_CONTACT_LINK_PERMISSIONS: Final[pet_contact_link_permission_data] = {
    "is_primary_contact": False,
    "is_emergency_contact": False,
    "can_authorize_treatment": False,
    "can_receive_medical_updates": False,
    "can_receive_billing": False,
    "can_pickup_pet": False,
}

AUDIT_ACTION_PET_CONTACT_LINK_CREATED = "PET_CONTACT_LINK_CREATED"
AUDIT_ENTITY_TYPE_PET_CONTACT_LINK = "Pet_Contact_Link"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _clean_upper_string(value: Any) -> str:
    return _clean_string(value).upper()


def _bool_value(value: Any) -> bool:
    return value is True


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _bool_from_any_key(
    data: dict[str, Any],
    *,
    keys: tuple[str, ...],
    default: bool,
) -> bool:
    for key in keys:
        if key in data:
            return _bool_value(data.get(key))

    return default


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


def _get_specific_relationship_from_payload(data: dict[str, Any]) -> str:
    return _clean_string(data.get("specific_relationship"))


def _get_pet_contact_link_notes_from_payload(data: dict[str, Any]) -> str:
    return _clean_string(
        data.get("pet_contact_link_notes")
        or data.get("pet_contact_notes")
    )


def _get_center_contact_id_from_payload(data: dict[str, Any]) -> int:
    raw_value = data.get("center_contact_id")

    if raw_value is None:
        raise ValidationError(
            {
                "center_contact_id": (
                    "Debes seleccionar un contacto del centro."
                )
            }
        )

    try:
        center_contact_id = int(raw_value)

    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {
                "center_contact_id": (
                    "El identificador del contacto del centro no es válido."
                )
            }
        ) from exc

    if center_contact_id <= 0:
        raise ValidationError(
            {
                "center_contact_id": (
                    "El identificador del contacto del centro no es válido."
                )
            }
        )

    return center_contact_id


def _get_existing_pet(
    *,
    center_id: int,
    pet_id: int,
) -> Pet:
    try:
        return (
            Pet.objects.select_for_update()
            .select_related("veterinary_center")
            .get(
                id=pet_id,
                veterinary_center_id=center_id,
            )
        )

    except Pet.DoesNotExist as exc:
        raise ValidationError(
            {
                "pet": "Paciente no encontrado.",
            }
        ) from exc


def _get_existing_center_contact(
    *,
    center_id: int,
    center_contact_id: int,
) -> Center_Contact:
    try:
        return Center_Contact.objects.select_for_update().get(
            id=center_contact_id,
            veterinary_center_id=center_id,
            soft_deleted_at__isnull=True,
        )
    except Center_Contact.DoesNotExist as exc:
        raise ValidationError(
            {
                "center_contact_id": (
                    "El contacto del centro seleccionado no existe, "
                    "no pertenece al centro indicado o fue eliminado."
                )
            }
        ) from exc


def _validate_center_contact_is_active(
    center_contact: Center_Contact,
) -> None:
    if center_contact.is_active:
        return

    raise ValidationError(
        {
            "center_contact_id": (
                "El contacto del centro seleccionado está inactivo "
                "y no puede vincularse a un paciente."
            )
        }
    )


def _validate_role_exists(role: str) -> None:
    allowed_values = {choice.value for choice in Choices_Pet_Contact_Link_Role}

    if role not in allowed_values:
        raise ValidationError(
            {
                "role": f"Rol de contacto inválido: {role}.",
            }
        )


def _validate_role_matches_center_contact_type(
    *,
    role: str,
    center_contact_type: str,
) -> None:
    if center_contact_type == Choices_Center_Contact_Type.PERSON.value:
        if not Choices_Pet_Contact_Link_Role.is_person_role(role):
            raise ValidationError(
                {
                    "role": (
                        "Para un contacto de tipo persona, selecciona un rol "
                        "válido para personas."
                    )
                }
            )

        return

    if center_contact_type == Choices_Center_Contact_Type.INSTITUTION.value:
        if not Choices_Pet_Contact_Link_Role.is_institution_role(role):
            raise ValidationError(
                {
                    "role": (
                        "Para un contacto de tipo institución, selecciona un rol "
                        "válido para instituciones."
                    )
                }
            )

        return

    raise ValidationError(
        {
            "center_contact_type": "Tipo de contacto inválido.",
        }
    )


def _build_pet_contact_link_permission_data(
    *,
    role: str,
    data: dict[str, Any],
) -> pet_contact_link_permission_data:
    """
    Builds permission data for a pet-contact link.

    Important:
    Permissions are not inferred automatically from the selected role.
    They are only taken from the explicit payload sent by the frontend.

    The only forced permission is can_receive_billing=True for the
    BILLING_RESPONSIBLE role, because that role is invalid without billing
    permission.
    """

    permission_data = dict(DEFAULT_PET_CONTACT_LINK_PERMISSIONS)

    permission_data["is_primary_contact"] = _bool_from_any_key(
        data,
        keys=("is_primary_contact",),
        default=permission_data["is_primary_contact"],
    )

    permission_data["is_emergency_contact"] = _bool_from_any_key(
        data,
        keys=("is_emergency_contact",),
        default=permission_data["is_emergency_contact"],
    )

    permission_data["can_authorize_treatment"] = _bool_from_any_key(
        data,
        keys=("can_authorize_treatment",),
        default=permission_data["can_authorize_treatment"],
    )

    permission_data["can_receive_medical_updates"] = _bool_from_any_key(
        data,
        keys=("can_receive_medical_updates",),
        default=permission_data["can_receive_medical_updates"],
    )

    permission_data["can_receive_billing"] = _bool_from_any_key(
        data,
        keys=("can_receive_billing",),
        default=permission_data["can_receive_billing"],
    )

    permission_data["can_pickup_pet"] = _bool_from_any_key(
        data,
        keys=("can_pickup_pet",),
        default=permission_data["can_pickup_pet"],
    )

    if role == Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value:
        permission_data["can_receive_billing"] = True

    return permission_data


def _get_existing_active_pet_contact_link(
    *,
    pet: Pet,
    center_contact: Center_Contact,
    role: str,
) -> Pet_Contact_Link | None:
    return (
        Pet_Contact_Link.objects.select_for_update()
        .filter(
            pet=pet,
            center_contact=center_contact,
            role=role,
            is_active=True,
        )
        .order_by("-id")
        .first()
    )


def _validate_contact_link_does_not_already_exist(
    *,
    existing_pet_contact_link: Pet_Contact_Link | None,
) -> None:
    if existing_pet_contact_link is None:
        return

    raise ValidationError(
        {
            "center_contact_id": (
                "Este contacto del centro ya está vinculado a este paciente "
                "con el rol seleccionado."
            )
        }
    )


def _validate_primary_contact_rule(
    *,
    pet: Pet,
    permission_data: pet_contact_link_permission_data,
) -> None:
    if not permission_data["is_primary_contact"]:
        return

    existing_primary_query = Pet_Contact_Link.objects.select_for_update().filter(
        pet=pet,
        is_primary_contact=True,
        is_active=True,
    )

    if existing_primary_query.exists():
        raise ValidationError(
            {
                "is_primary_contact": (
                    "Este paciente ya tiene un contacto principal activo."
                )
            }
        )


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
        "created_at": _serialize_datetime(
            getattr(pet_contact_link, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(pet_contact_link, "updated_at", None)
        ),
    }


def _create_pet_contact_link_created_audit_log(
    *,
    pet_contact_link: Pet_Contact_Link,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=pet_contact_link.pet.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_PET_CONTACT_LINK_CREATED,
        entity_type=AUDIT_ENTITY_TYPE_PET_CONTACT_LINK,
        entity_id=pet_contact_link.id,
        reason=_clean_string(reason),
        old_values={},
        new_values=_build_pet_contact_link_audit_values(pet_contact_link),
    )


def _create_pet_contact_link(
    *,
    pet: Pet,
    center_contact: Center_Contact,
    role: str,
    defaults: dict[str, Any],
    member: Center_Staff_Member,
) -> Pet_Contact_Link:
    pet_contact_link = Pet_Contact_Link(
        pet=pet,
        center_contact=center_contact,
        role=role,
        created_by=member,
        **defaults,
    )

    pet_contact_link.full_clean()
    pet_contact_link.save()

    return pet_contact_link


@transaction.atomic
def add_pet_contact_link_to_pet(
    *,
    center_id: int,
    pet_id: int,
    data: dict[str, Any],
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None = None,
) -> Pet_Contact_Link:
    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=center_id,
    )

    pet = _get_existing_pet(
        center_id=center_id,
        pet_id=pet_id,
    )

    role = _clean_upper_string(data.get("role"))

    _validate_role_exists(role)

    center_contact_id = _get_center_contact_id_from_payload(data)

    center_contact = _get_existing_center_contact(
        center_id=center_id,
        center_contact_id=center_contact_id,
    )

    _validate_center_contact_is_active(center_contact)

    _validate_role_matches_center_contact_type(
        role=role,
        center_contact_type=center_contact.center_contact_type,
    )

    permission_data = _build_pet_contact_link_permission_data(
        role=role,
        data=data,
    )

    existing_pet_contact_link = _get_existing_active_pet_contact_link(
        pet=pet,
        center_contact=center_contact,
        role=role,
    )

    _validate_contact_link_does_not_already_exist(
        existing_pet_contact_link=existing_pet_contact_link,
    )

    _validate_primary_contact_rule(
        pet=pet,
        permission_data=permission_data,
    )

    pet_contact_link_defaults: dict[str, Any] = {
        "specific_relationship": _get_specific_relationship_from_payload(data),
        "notes": _get_pet_contact_link_notes_from_payload(data),
        "is_active": True,
        **permission_data,
    }

    pet_contact_link = _create_pet_contact_link(
        pet=pet,
        center_contact=center_contact,
        role=role,
        defaults=pet_contact_link_defaults,
        member=member,
    )

    _create_pet_contact_link_created_audit_log(
        pet_contact_link=pet_contact_link,
        actor=actor,
        member=member,
        reason=reason,
    )

    return pet_contact_link


__all__ = [
    "add_pet_contact_link_to_pet",
]