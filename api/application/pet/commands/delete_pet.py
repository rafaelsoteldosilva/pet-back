# api/application/pet/commands/delete_pet.py

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from django.core.exceptions import (
    ObjectDoesNotExist,
    ValidationError as DjangoValidationError,
)
from django.db import transaction
from django.db.models import Model
from rest_framework.exceptions import PermissionDenied

from api.domains.pet.errors import (
    PetCannotBeDeletedBecauseClinicalRecordsExistError,
    PetCannotBeDeletedByDifferentUserError,
    PetRuleViolationError,
)
from api.domains.pet.rules import ensure_pet_can_be_deleted
from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import Center_Staff_Membership
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.models.user import Pet_Control_User
from api.shared.choices.choices import Choices_Role


PET_DELETE_ALLOWED_ROLES: set[str] = {
    Choices_Role.CENTER_ADMIN.value,
    Choices_Role.VETERINARIAN.value,
    Choices_Role.RECEPTIONIST.value,
}

AUDIT_ACTION_PET_DELETED = "PET_DELETED"
AUDIT_ENTITY_TYPE_PET = "Pet"
DEFAULT_DELETE_PET_REASON = "Eliminación de paciente."


# Important:
# This command gathers ORM facts.
# The domain rule itself lives in api/domains/pet/rules.py.
#
# Add your real clinical model names here if they differ.
# The keys are normalized to lowercase.
CLINICAL_RELATED_MODEL_LABELS: dict[str, str] = {
    "consultation": "consultas",
    "petconsultation": "consultas",
    "pet_consultation": "consultas",
    "clinicalconsultation": "consultas",
    "clinical_consultation": "consultas",
    "medicalconsultation": "consultas",
    "medical_consultation": "consultas",
    "vaccine": "vacunas",
    "petvaccine": "vacunas",
    "pet_vaccine": "vacunas",
    "vaccination": "vacunas",
    "petvaccination": "vacunas",
    "pet_vaccination": "vacunas",
    "appliedvaccine": "vacunas",
    "applied_vaccine": "vacunas",
    "petappliedvaccine": "vacunas",
    "pet_applied_vaccine": "vacunas",
}


class PetNotFoundError(Exception):
    pass


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _normalize_identifier(value: str) -> str:
    return (
        str(value)
        .strip()
        .lower()
        .replace(".", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )


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


def _ensure_membership_can_delete_pet(
    *,
    membership: Center_Staff_Membership,
) -> None:
    actor_role = _get_membership_role(membership)

    if actor_role not in PET_DELETE_ALLOWED_ROLES:
        raise PermissionDenied(
            "No tienes permiso para eliminar pacientes."
        )


def _get_pet_or_raise(
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


def _related_accessor_has_records(
    *,
    pet: Pet,
    accessor_name: str,
) -> bool:
    try:
        related_value: Any = getattr(pet, accessor_name)
    except ObjectDoesNotExist:
        return False

    if related_value is None:
        return False

    exists_method: Any = getattr(related_value, "exists", None)

    if callable(exists_method):
        exists_callable = cast(Callable[[], bool], exists_method)

        return bool(exists_callable())

    count_method: Any = getattr(related_value, "count", None)

    if callable(count_method):
        count_callable = cast(Callable[[], int], count_method)

        return count_callable() > 0

    return True


def _get_clinical_relation_display_label(
    *,
    model_name: str,
    model_label: str,
    model_label_lower: str,
) -> str | None:
    identifiers = {
        _normalize_identifier(model_name),
        _normalize_identifier(model_label),
        _normalize_identifier(model_label_lower),
    }

    for identifier in identifiers:
        display_label = CLINICAL_RELATED_MODEL_LABELS.get(identifier)

        if display_label:
            return display_label

    return None


def _collect_pet_deletion_clinical_record_sources(
    *,
    pet: Pet,
) -> list[str]:
    sources: set[str] = set()

    for relation in pet._meta.related_objects:
        related_model_raw: object = getattr(
            relation,
            "related_model",
            None,
        )

        if not isinstance(related_model_raw, type):
            continue

        related_model = cast(type[Model], related_model_raw)
        related_model_meta: Any = getattr(related_model, "_meta", None)

        if related_model_meta is None:
            continue

        model_name = str(getattr(related_model, "__name__", ""))
        model_label = str(getattr(related_model_meta, "label", ""))
        model_label_lower = str(
            getattr(related_model_meta, "label_lower", "")
        )

        display_label = _get_clinical_relation_display_label(
            model_name=model_name,
            model_label=model_label,
            model_label_lower=model_label_lower,
        )

        if not display_label:
            continue

        get_accessor_name_method: Any = getattr(
            relation,
            "get_accessor_name",
            None,
        )

        if not callable(get_accessor_name_method):
            continue

        get_accessor_name = cast(
            Callable[[], str | None],
            get_accessor_name_method,
        )

        accessor_name = get_accessor_name()

        if not accessor_name:
            continue

        if _related_accessor_has_records(
            pet=pet,
            accessor_name=accessor_name,
        ):
            sources.add(display_label)

    return sorted(sources)


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


def _raise_django_validation_error_for_delete_rule(
    exc: PetRuleViolationError,
) -> None:
    error_data: dict[str, Any] = {
        "pet": [
            str(exc),
        ],
    }

    clinical_record_sources = getattr(
        exc,
        "clinical_record_sources",
        None,
    )

    if clinical_record_sources is not None:
        error_data["clinical_record_sources"] = list(
            clinical_record_sources,
        )

    raise DjangoValidationError(error_data) from exc

def delete_pet(
    *,
    center_id: int,
    pet_id: int,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    reason: str | None = None,
) -> None:
    """
    Deletes a pet when domain rules allow it.

    Domain rule:
    - A pet cannot be deleted when it has clinical records.

    This command is responsible for:
    - permission checks
    - loading ORM data
    - collecting facts for the domain rule
    - deleting the Pet
    - writing audit log
    """

    with transaction.atomic():
        _validate_actor_membership_for_center(
            actor=actor,
            membership=membership,
            center_id=center_id,
        )

        _ensure_membership_can_delete_pet(
            membership=membership,
        )

        pet = _get_pet_or_raise(
            center_id=center_id,
            pet_id=pet_id,
        )

        clinical_record_sources = (
            _collect_pet_deletion_clinical_record_sources(
                pet=pet,
            )
        )

        try:
            ensure_pet_can_be_deleted(
                clinical_record_sources=clinical_record_sources,
                actor_user_id=actor.id,
                pet_created_by_user_id=pet.created_by_id,
            )
        except (
            PetCannotBeDeletedBecauseClinicalRecordsExistError,
            PetCannotBeDeletedByDifferentUserError,
        ) as exc:
            _raise_django_validation_error_for_delete_rule(exc)

        old_values = _build_pet_old_values(
            pet=pet,
        )

        actor_role = _get_membership_role(membership)
        audit_reason = _clean_string(reason) or DEFAULT_DELETE_PET_REASON

        pet.delete()

        Audit_Log.objects.create(
            veterinary_center_id=center_id,
            actor_user=actor,
            actor_role=actor_role,
            action=AUDIT_ACTION_PET_DELETED,
            entity_type=AUDIT_ENTITY_TYPE_PET,
            entity_id=pet_id,
            reason=audit_reason,
            old_values=old_values,
            new_values={},
            metadata={
                "delete_type": "hard_delete",
                "clinical_record_sources": clinical_record_sources,
            },
        )


__all__ = [
    "delete_pet",
    "PetNotFoundError",
]