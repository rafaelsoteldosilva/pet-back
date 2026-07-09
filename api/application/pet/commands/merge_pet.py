# api/application/pet/commands/merge_pet.py

from __future__ import annotations

from typing import Any, Iterable

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Model
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from api.infrastructure.orm.models import (
    Consultation,
    Pet,
    Pet_Disease_Case,
    Pet_Problem_Case,
)
from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import Center_Staff_Member
from api.infrastructure.orm.models.pet import Pet_Contact_Link
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import Choices_Pet_Status

AUDIT_ACTION_PET_MERGED = "PET_MERGED"
AUDIT_ENTITY_TYPE_PET = "Pet"


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


def _raise_validation_error_from_django_error(
    exc: DjangoValidationError,
) -> None:
    """
    Converts Django model validation errors into DRF validation errors.
    """

    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict) from exc

    raise ValidationError({"detail": exc.messages}) from exc


def _save_model(
    instance: Model,
    *,
    update_fields: Iterable[str] | None = None,
) -> None:
    """
    Saves a Django model instance.

    Model validation is handled by FullCleanOnSaveMixin inside model.save().
    """

    try:
        instance.save(update_fields=update_fields)
    except DjangoValidationError as exc:
        _raise_validation_error_from_django_error(exc)


def _model_field_exists(
    *,
    instance: Model,
    field_name: str,
) -> bool:
    try:
        instance._meta.get_field(field_name)
    except Exception:
        return False

    return True


def _get_existing_update_fields(
    *,
    instance: Model,
    field_names: Iterable[str],
) -> list[str]:
    return [
        field_name
        for field_name in field_names
        if _model_field_exists(instance=instance, field_name=field_name)
    ]


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


def _move_pet_related_records_to_master(
    *,
    queryset: Any,
    master: Pet,
) -> None:
    """
    Moves records from the secondary pet to the master pet.

    Do not use queryset.update(pet=master) here because update() bypasses:
    - save()
    - model validation
    - FullCleanOnSaveMixin
    """

    for instance in queryset.select_for_update():
        instance.pet = master
        _save_model(instance, update_fields=["pet"])


def _get_pet_for_merge(
    *,
    pet_id: int,
    field_name: str,
) -> Pet:
    try:
        return Pet.objects.select_for_update().get(pk=pet_id)
    except Pet.DoesNotExist as exc:
        raise ValidationError(
            {
                field_name: ["Patient not found."],
            }
        ) from exc


def _get_resolved_master_pet(master: Pet) -> Pet:
    """
    Returns the active/root master pet.

    If the requested master pet was already merged into another pet, the merge
    should use the real master. The resolved master is locked too, because the
    merge will move records into it.
    """

    if master.master_pet_id is None:
        return master

    try:
        return Pet.objects.select_for_update().get(pk=master.master_pet_id)
    except Pet.DoesNotExist as exc:
        raise ValidationError(
            {
                "master_pet_id": [
                    "The resolved master patient was not found.",
                ]
            }
        ) from exc


def _get_pet_related_record_ids(pet: Pet) -> dict[str, list[int]]:
    return {
        "consultation_ids": list(
            Consultation.objects.filter(pet=pet).values_list(
                "id",
                flat=True,
            )
        ),
        "disease_case_ids": list(
            Pet_Disease_Case.objects.filter(pet=pet).values_list(
                "id",
                flat=True,
            )
        ),
        "problem_case_ids": list(
            Pet_Problem_Case.objects.filter(pet=pet).values_list(
                "id",
                flat=True,
            )
        ),
        "pet_contact_link_ids": list(
            Pet_Contact_Link.objects.filter(pet=pet).values_list(
                "id",
                flat=True,
            )
        ),
    }


def _get_pet_related_record_counts(pet: Pet) -> dict[str, int]:
    return {
        "consultations": Consultation.objects.filter(pet=pet).count(),
        "disease_cases": Pet_Disease_Case.objects.filter(pet=pet).count(),
        "problem_cases": Pet_Problem_Case.objects.filter(pet=pet).count(),
        "pet_contact_links": Pet_Contact_Link.objects.filter(pet=pet).count(),
    }


def _get_moved_record_counts(
    moved_record_ids: dict[str, list[int]],
) -> dict[str, int]:
    return {
        key.replace("_ids", "s"): len(value)
        for key, value in moved_record_ids.items()
    }


def _build_pet_merge_audit_values(pet: Pet) -> dict[str, Any]:
    return {
        "id": pet.id,
        "veterinary_center_id": pet.veterinary_center_id,
        "history_code": getattr(pet, "history_code", ""),
        "name": pet.name,
        "status": pet.status,
        "master_pet_id": pet.master_pet_id,
        "archived_at": _serialize_datetime(
            getattr(pet, "archived_at", None)
        ),
        "merged_at": _serialize_datetime(
            getattr(pet, "merged_at", None)
        ),
        "merged_by_id": getattr(pet, "merged_by_id", None),
        "updated_at": _serialize_datetime(
            getattr(pet, "updated_at", None)
        ),
        "soft_deleted_at": _serialize_datetime(
            getattr(pet, "soft_deleted_at", None)
        ),
        "soft_deleted_by_id": getattr(pet, "soft_deleted_by_id", None),
    }


def _set_merged_by(
    *,
    secondary: Pet,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
) -> None:
    try:
        merged_by_field = secondary._meta.get_field("merged_by")
    except Exception as exc:
        raise ValidationError(
            {
                "merged_by": [
                    "The Pet model does not define a merged_by field.",
                ]
            }
        ) from exc

    remote_field = getattr(merged_by_field, "remote_field", None)
    remote_model = getattr(remote_field, "model", None)
    remote_model_name = getattr(remote_model, "__name__", "")

    if remote_model_name == "Pet_Control_User":
        setattr(secondary, "merged_by", actor)
        return

    if remote_model_name == "Center_Staff_Member":
        setattr(secondary, "merged_by", member)
        return

    raise ValidationError(
        {
            "merged_by": [
                "Unsupported merged_by target model: "
                f"{remote_model_name or 'unknown'}."
            ]
        }
    )


def _create_pet_merged_audit_log(
    *,
    veterinary_center_id: int,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None,
    secondary_pet_id: int,
    old_values: dict[str, Any],
    new_values: dict[str, Any],
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_member_role(member),
        action=AUDIT_ACTION_PET_MERGED,
        entity_type=AUDIT_ENTITY_TYPE_PET,
        entity_id=secondary_pet_id,
        reason=_clean_string(reason),
        old_values=old_values,
        new_values=new_values,
    )


@transaction.atomic
def merge_pet(
    *,
    master_pet_id: int,
    secondary_pet_id: int,
    actor: Pet_Control_User,
    member: Center_Staff_Member,
    reason: str | None = None,
) -> None:
    if master_pet_id == secondary_pet_id:
        raise ValidationError(
            {
                "detail": [
                    "The master pet and secondary pet must be different patients."
                ]
            }
        )

    requested_master = _get_pet_for_merge(
        pet_id=master_pet_id,
        field_name="master_pet_id",
    )

    secondary = _get_pet_for_merge(
        pet_id=secondary_pet_id,
        field_name="secondary_pet_id",
    )

    master = _get_resolved_master_pet(requested_master)

    if master.id == secondary.id:
        raise ValidationError(
            {
                "detail": [
                    "The resolved master pet and secondary pet must be different patients."
                ]
            }
        )

    if master.veterinary_center_id != secondary.veterinary_center_id:
        raise ValidationError(
            {
                "detail": [
                    "Both patients must belong to the same veterinary center."
                ]
            }
        )

    _validate_actor_member_for_center(
        actor=actor,
        member=member,
        center_id=master.veterinary_center_id,
    )

    if secondary.master_pet_id is not None:
        raise ValidationError(
            {
                "secondary_pet_id": [
                    "The secondary patient is already merged into another patient."
                ]
            }
        )

    moved_record_ids = _get_pet_related_record_ids(secondary)

    old_values = {
        "requested_master_pet_id": requested_master.id,
        "resolved_master_pet_before": _build_pet_merge_audit_values(master),
        "secondary_pet_before": _build_pet_merge_audit_values(secondary),
        "master_related_record_counts_before": (
            _get_pet_related_record_counts(master)
        ),
        "secondary_related_record_counts_before": (
            _get_pet_related_record_counts(secondary)
        ),
        "records_to_move_from_secondary_to_master": moved_record_ids,
    }

    # Move clinical data.
    _move_pet_related_records_to_master(
        queryset=Consultation.objects.filter(pet=secondary),
        master=master,
    )

    _move_pet_related_records_to_master(
        queryset=Pet_Disease_Case.objects.filter(pet=secondary),
        master=master,
    )

    _move_pet_related_records_to_master(
        queryset=Pet_Problem_Case.objects.filter(pet=secondary),
        master=master,
    )

    # Move contact relations.
    #
    # This can correctly fail if moving contacts creates invalid data, for example:
    # - duplicated active pet/contact/role relation
    # - more than one active primary contact for the same pet
    #
    # The merge should not silently create invalid data.
    _move_pet_related_records_to_master(
        queryset=Pet_Contact_Link.objects.filter(pet=secondary),
        master=master,
    )

    now = timezone.now()

    secondary.master_pet = master
    secondary.status = Choices_Pet_Status.ARCHIVED.value
    secondary.archived_at = now
    secondary.merged_at = now

    _set_merged_by(
        secondary=secondary,
        actor=actor,
        member=member,
    )

    _save_model(
        secondary,
        update_fields=_get_existing_update_fields(
            instance=secondary,
            field_names=[
                "master_pet",
                "status",
                "archived_at",
                "merged_at",
                "merged_by",
                "updated_at",
            ],
        ),
    )

    new_values = {
        "requested_master_pet_id": requested_master.id,
        "resolved_master_pet_after": _build_pet_merge_audit_values(master),
        "secondary_pet_after": _build_pet_merge_audit_values(secondary),
        "master_related_record_counts_after": (
            _get_pet_related_record_counts(master)
        ),
        "secondary_related_record_counts_after": (
            _get_pet_related_record_counts(secondary)
        ),
        "records_moved_from_secondary_to_master": moved_record_ids,
        "moved_record_counts": _get_moved_record_counts(moved_record_ids),
    }

    _create_pet_merged_audit_log(
        veterinary_center_id=master.veterinary_center_id,
        actor=actor,
        member=member,
        reason=reason,
        secondary_pet_id=secondary.id,
        old_values=old_values,
        new_values=new_values,
    )


__all__ = [
    "merge_pet",
]