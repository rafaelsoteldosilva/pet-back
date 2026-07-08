# api/application/pet/commands/create_pet.py

"""
Application command: Create Pet.

Responsabilidad
---------------
Crear un nuevo paciente veterinario.

La capa application:
- coordina dominio e infraestructura
- usa ORM o repositories
- emite eventos si es necesario
- registra auditoría de acciones importantes
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from api.application.pet.commands.add_pet_contact_link import (
    add_pet_contact_link_to_pet,
)
from api.domains.pet.errors import (
    PetBreedDoesNotBelongToSpeciesError,
    PetRuleViolationError,
    PetSpeciesNotAllowedForCenterError,
)
from api.domains.pet.rules import (
    validate_pet_species_and_breed_for_center,
)
from api.infrastructure.orm.models.audit import Audit_Log
from api.infrastructure.orm.models.center import Center_Staff_Membership
from api.infrastructure.orm.models.pet import Pet
from api.infrastructure.orm.models.user import Pet_Control_User
from api.infrastructure.orm.selectors.catalog import (
    get_allowed_species_ids_for_center,
    get_species_id_for_breed,
)

AUDIT_ACTION_PET_CREATED = "PET_CREATED"
AUDIT_ENTITY_TYPE_PET = "Pet"


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _clean_optional_string(value: Any) -> str | None:
    cleaned = _clean_string(value)

    if not cleaned:
        return None

    return cleaned


def _serialize_date(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _serialize_datetime(value: Any) -> str | None:
    if value is None:
        return None

    isoformat = getattr(value, "isoformat", None)

    if callable(isoformat):
        return str(isoformat())

    return str(value)


def _extract_int_id(
    field_name: str,
    value: Any,
    *,
    required: bool,
) -> int | None:
    if value in (None, ""):
        if required:
            raise ValidationError({field_name: ["This field is required."]})

        return None

    if hasattr(value, "id"):
        value = value.id

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {
                field_name: ["A valid integer is required."],
            }
        ) from exc


def _coerce_required_int(field_name: str, value: Any) -> int:
    coerced = _extract_int_id(
        field_name,
        value,
        required=True,
    )

    if coerced is None:
        raise ValidationError({field_name: ["This field is required."]})

    return coerced


def _coerce_optional_int(field_name: str, value: Any) -> int | None:
    return _extract_int_id(
        field_name,
        value,
        required=False,
    )


def _raise_validation_error_for_rule_violation(
    exc: PetRuleViolationError,
) -> None:
    if isinstance(exc, PetSpeciesNotAllowedForCenterError):
        raise ValidationError(
            {
                "species_id": [
                    "This species is not enabled for this veterinary center.",
                ]
            }
        ) from exc

    if isinstance(exc, PetBreedDoesNotBelongToSpeciesError):
        raise ValidationError(
            {
                "breed_id": [
                    "The selected breed does not belong to the selected species.",
                ]
            }
        ) from exc

    raise ValidationError({"detail": [str(exc)]}) from exc


def _raise_validation_error_from_django_error(
    exc: DjangoValidationError,
) -> None:
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict) from exc

    raise ValidationError({"detail": exc.messages}) from exc


def _validate_actor_membership_for_center(
    *,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    center_id: int,
) -> None:
    if membership.veterinary_center_id != center_id:
        raise PermissionError(
            "La membresía activa no pertenece al centro veterinario indicado."
        )

    if membership.user_id != actor.id:
        raise PermissionError(
            "La membresía activa no pertenece al usuario autenticado."
        )

    if not membership.is_active:
        raise PermissionError(
            "La membresía del usuario en este centro no está activa."
        )

    if not membership.veterinary_center.is_active:
        raise PermissionError(
            "El centro veterinario no está activo."
        )


def _validate_last_attending_vet_for_center(
    *,
    veterinary_center_id: int,
    last_attending_vet_id: int | None,
) -> None:
    if last_attending_vet_id is None:
        return

    exists = Center_Staff_Membership.objects.filter(
        id=last_attending_vet_id,
        veterinary_center_id=veterinary_center_id,
        is_active=True,
        user__is_active=True,
    ).exists()

    if not exists:
        raise ValidationError(
            {
                "last_attending_vet_id": [
                    "The selected veterinarian does not belong to this center.",
                ]
            }
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


def _get_membership_role(membership: Center_Staff_Membership) -> str:
    role = getattr(membership, "role", "")

    return _clean_string(getattr(role, "value", role))


def _normalize_contact_links_for_create(
    contact_links: Any,
) -> list[dict[str, Any]]:
    if not isinstance(contact_links, list):
        raise ValidationError(
            {
                "contact_links": [
                    "La lista de contactos del paciente es obligatoria.",
                ]
            }
        )

    if len(contact_links) == 0:
        raise ValidationError(
            {
                "contact_links": [
                    "Debes agregar al menos un contacto principal.",
                ]
            }
        )

    normalized_links: list[dict[str, Any]] = []
    selected_contact_ids: set[int] = set()
    primary_count = 0

    for index, raw_link in enumerate(contact_links):
        if not isinstance(raw_link, dict):
            raise ValidationError(
                {
                    "contact_links": [
                        f"El contacto #{index + 1} no tiene un formato válido.",
                    ]
                }
            )

        center_contact_id = _coerce_required_int(
            "center_contact_id",
            raw_link.get("center_contact_id"),
        )

        if center_contact_id in selected_contact_ids:
            raise ValidationError(
                {
                    "contact_links": [
                        "No puedes agregar el mismo contacto más de una vez.",
                    ]
                }
            )

        selected_contact_ids.add(center_contact_id)

        role = _clean_string(raw_link.get("role")).upper()

        if not role:
            raise ValidationError(
                {
                    "contact_links": [
                        f"El contacto #{index + 1} no tiene rol asignado.",
                    ]
                }
            )

        is_primary_contact = raw_link.get("is_primary_contact") is True

        if is_primary_contact:
            primary_count += 1

        can_receive_billing = (
            True
            if role == "BILLING_RESPONSIBLE"
            else raw_link.get("can_receive_billing") is True
        )

        normalized_links.append(
            {
                "center_contact_id": center_contact_id,
                "role": role,
                "specific_relationship": _clean_optional_string(
                    raw_link.get("specific_relationship"),
                ),
                "is_primary_contact": is_primary_contact,
                "is_emergency_contact": (
                    raw_link.get("is_emergency_contact") is True
                ),
                "can_authorize_treatment": (
                    raw_link.get("can_authorize_treatment") is True
                ),
                "can_receive_medical_updates": (
                    raw_link.get("can_receive_medical_updates") is True
                ),
                "can_receive_billing": can_receive_billing,
                "can_pickup_pet": raw_link.get("can_pickup_pet") is True,
                "pet_contact_notes": _clean_optional_string(
                    raw_link.get("pet_contact_notes")
                    or raw_link.get("pet_contact_link_notes"),
                ),
            }
        )

    if primary_count == 0:
        raise ValidationError(
            {
                "contact_links": [
                    "Debes marcar un contacto principal.",
                ]
            }
        )

    if primary_count > 1:
        raise ValidationError(
            {
                "contact_links": [
                    "Solo puede haber un contacto principal.",
                ]
            }
        )

    return normalized_links


def _build_pet_audit_values(pet: Pet) -> dict[str, Any]:
    return {
        "id": pet.id,
        "veterinary_center_id": pet.veterinary_center_id,
        "history_code": getattr(pet, "history_code", ""),
        "name": pet.name,
        "sex": pet.sex,
        "species_id": pet.species_id,
        "breed_id": pet.breed_id,
        "sterilized": pet.sterilized,
        "birth_date": _serialize_date(pet.birth_date),
        "body_description": getattr(pet, "body_description", None),
        "size": getattr(pet, "size", None),
        "last_weight": (
            str(pet.last_weight)
            if getattr(pet, "last_weight", None) is not None
            else None
        ),
        "last_attending_vet_id": getattr(
            pet,
            "last_attending_vet_id",
            None,
        ),
        "reference": getattr(pet, "reference", None),
        "has_pedigree": getattr(pet, "has_pedigree", False),
        "pedigree_registry": getattr(pet, "pedigree_registry", None),
        "has_visual_identification": getattr(
            pet,
            "has_visual_identification",
            False,
        ),
        "visual_tag": getattr(pet, "visual_tag", None),
        "visual_identification_or_tattoo_description": getattr(
            pet,
            "visual_identification_or_tattoo_description",
            None,
        ),
        "has_microchip": getattr(pet, "has_microchip", False),
        "microchip_code": getattr(pet, "microchip_code", None),
        "microchip_date": _serialize_date(
            getattr(pet, "microchip_date", None)
        ),
        "microchip_body_region": getattr(
            pet,
            "microchip_body_region",
            None,
        ),
        "clinical_observations": getattr(
            pet,
            "clinical_observations",
            None,
        ),
        "internal_notes": getattr(pet, "internal_notes", None),
        "photo_url": getattr(pet, "photo_url", None),
        "status": getattr(pet, "status", ""),
        "clinical_record_status": getattr(
            pet,
            "clinical_record_status",
            "",
        ),
        "is_active": getattr(pet, "is_active", True),
        "created_at": _serialize_datetime(
            getattr(pet, "created_at", None)
        ),
        "updated_at": _serialize_datetime(
            getattr(pet, "updated_at", None)
        ),
        "soft_deleted_at": _serialize_datetime(
            getattr(pet, "soft_deleted_at", None)
        ),
        "soft_deleted_by_id": getattr(pet, "soft_deleted_by_id", None),
    }


def _create_pet_created_audit_log(
    *,
    pet: Pet,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    reason: str | None,
) -> None:
    Audit_Log.objects.create(
        veterinary_center_id=pet.veterinary_center_id,
        actor_user_id=actor.id,
        actor_display_name=_get_actor_display_name(actor),
        actor_role=_get_membership_role(membership),
        action=AUDIT_ACTION_PET_CREATED,
        entity_type=AUDIT_ENTITY_TYPE_PET,
        entity_id=pet.id,
        reason=_clean_string(reason),
        old_values={},
        new_values=_build_pet_audit_values(pet),
    )


@transaction.atomic
def create_pet(
    *,
    veterinary_center_id: int,
    name: str,
    sex: str,
    species_id: int,
    actor: Pet_Control_User,
    membership: Center_Staff_Membership,
    contact_links: list[dict[str, Any]],
    breed_id: int | None = None,
    sterilized: bool = False,
    birth_date: date | None = None,
    body_description: str | None = None,
    size: str | None = None,
    last_weight: Decimal | None = None,
    last_attending_vet_id: int | None = None,
    reference: str | None = None,
    has_pedigree: bool = False,
    pedigree_registry: str | None = None,
    has_visual_identification: bool = False,
    visual_tag: str | None = None,
    visual_identification_or_tattoo_description: str | None = None,
    has_microchip: bool = False,
    microchip_code: str | None = None,
    microchip_date: date | None = None,
    microchip_body_region: str | None = None,
    clinical_observations: str | None = None,
    internal_notes: str | None = None,
    photo_url: str | None = None,
    reason: str | None = None,
) -> Pet:
    _validate_actor_membership_for_center(
        actor=actor,
        membership=membership,
        center_id=veterinary_center_id,
    )

    normalized_contact_links = _normalize_contact_links_for_create(
        contact_links,
    )

    normalized_species_id = _coerce_required_int("species_id", species_id)
    normalized_breed_id = _coerce_optional_int("breed_id", breed_id)
    normalized_last_attending_vet_id = _coerce_optional_int(
        "last_attending_vet_id",
        last_attending_vet_id,
    )

    allowed_species_ids = get_allowed_species_ids_for_center(
        veterinary_center_id=veterinary_center_id,
    )

    breed_species_id = None

    if normalized_breed_id is not None:
        breed_species_id = get_species_id_for_breed(normalized_breed_id)

    try:
        validate_pet_species_and_breed_for_center(
            veterinary_center_id=veterinary_center_id,
            species_id=normalized_species_id,
            allowed_species_ids=allowed_species_ids,
            breed_id=normalized_breed_id,
            breed_species_id=breed_species_id,
        )
    except PetRuleViolationError as exc:
        _raise_validation_error_for_rule_violation(exc)

    _validate_last_attending_vet_for_center(
        veterinary_center_id=veterinary_center_id,
        last_attending_vet_id=normalized_last_attending_vet_id,
    )

    cleaned_name = _clean_string(name)

    if not cleaned_name:
        raise ValidationError({"name": ["This field is required."]})

    cleaned_has_pedigree = bool(has_pedigree)
    cleaned_has_microchip = bool(has_microchip)

    cleaned_visual_tag = _clean_optional_string(visual_tag)
    cleaned_visual_identification_or_tattoo_description = (
        _clean_optional_string(
            visual_identification_or_tattoo_description,
        )
    )

    cleaned_has_visual_identification = bool(
        has_visual_identification
        or cleaned_visual_tag
        or cleaned_visual_identification_or_tattoo_description
    )

    pet = Pet(
        veterinary_center_id=veterinary_center_id,
        name=cleaned_name,
        sex=sex,
        species_id=normalized_species_id,
        breed_id=normalized_breed_id,
        sterilized=bool(sterilized),
        birth_date=birth_date,
        body_description=_clean_optional_string(body_description),
        size=_clean_optional_string(size),
        last_weight=last_weight,
        last_attending_vet_id=normalized_last_attending_vet_id,
        reference=_clean_optional_string(reference),
        has_pedigree=cleaned_has_pedigree,
        pedigree_registry=(
            _clean_optional_string(pedigree_registry)
            if cleaned_has_pedigree
            else None
        ),
        has_visual_identification=cleaned_has_visual_identification,
        visual_tag=cleaned_visual_tag,
        visual_identification_or_tattoo_description=(
            cleaned_visual_identification_or_tattoo_description
        ),
        has_microchip=cleaned_has_microchip,
        microchip_code=(
            _clean_optional_string(microchip_code)
            if cleaned_has_microchip
            else None
        ),
        microchip_date=(
            microchip_date
            if cleaned_has_microchip
            else None
        ),
        microchip_body_region=(
            _clean_optional_string(microchip_body_region)
            if cleaned_has_microchip
            else None
        ),
        clinical_observations=_clean_optional_string(
            clinical_observations
        ),
        internal_notes=_clean_optional_string(internal_notes),
        photo_url=_clean_optional_string(photo_url),
    )

    try:
        pet.assign_history_code_if_missing()
        pet.full_clean()
        pet.save()
    except DjangoValidationError as exc:
        _raise_validation_error_from_django_error(exc)

    for contact_link in normalized_contact_links:
        try:
            add_pet_contact_link_to_pet(
                center_id=veterinary_center_id,
                pet_id=pet.id,
                data=contact_link,
                actor=actor,
                membership=membership,
                reason=reason,
            )
        except DjangoValidationError as exc:
            _raise_validation_error_from_django_error(exc)

    _create_pet_created_audit_log(
        pet=pet,
        actor=actor,
        membership=membership,
        reason=reason,
    )

    return pet


__all__ = [
    "create_pet",
]