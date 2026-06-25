# api/application/pet/queries/get_all_pets_for_center.py

from __future__ import annotations

from typing import Optional

from django.db.models import Prefetch, Q, QuerySet

from api.application.pet.dto.pet_data_dto import (
    Pet_Data_DTO,
)
from api.application.pet.queries.get_pet_data import from_model
from api.infrastructure.orm.models.pet import Pet, Pet_Contact_Link
from api.shared.choices.choices import Choices_Pet_Contact_Link_Role


Role = Choices_Pet_Contact_Link_Role


PET_CONTACT_LINK_TEXT_SEARCH_TYPE_ALIASES = {
    "contact",
    "contacts",

    # Legacy/generic aliases. Keep only if the frontend still sends them.
    "responsible",
    "responsibles",
}


def get_all_pets_for_center(
    *,
    veterinary_center_id: Optional[int] = None,
    center_id: Optional[int] = None,
    search_type: Optional[str] = None,
    get_all_pets_for_center_type: Optional[str] = None,
    query: Optional[str] = None,
) -> list[Pet_Data_DTO]:
    """
    Returns pets for a veterinary center, optionally filtered by search type.

    Pet-contact-link search rule:
    - Pet links to Pet_Contact_Link through the reverse relation:
      pet_pet_contact_links.
    - Pet_Contact_Link links to Center_Contact through:
      center_contact.
    - Do not use old paths such as:
      pet_contacts__...
      pet_contacts__contact__...
      pet_pet_contact_links__contact__...
    """

    resolved_center_id = (
        veterinary_center_id
        if veterinary_center_id is not None
        else center_id
    )

    resolved_search_type = (
        search_type
        if search_type is not None
        else get_all_pets_for_center_type
    )

    if resolved_center_id is None:
        raise ValueError("veterinary_center_id is required.")

    normalized_search_type = _normalize_search_type(resolved_search_type)
    normalized_query = _normalize_query(query)

    qs = _base_queryset(center_id=resolved_center_id)

    if normalized_query:
        qs = _apply_search_filter(
            qs=qs,
            search_type=normalized_search_type,
            query=normalized_query,
        )

    qs = qs.distinct().order_by("name", "history_code", "id")

    return [from_model(pet) for pet in qs]


def _base_queryset(*, center_id: int) -> QuerySet[Pet]:
    return (
        Pet.objects.filter(veterinary_center_id=center_id)
        .select_related(
            "species",
            "species__global_species",
            "breed",
            "breed__global_breed",
            "last_attending_vet",
            "veterinary_center",
        )
        .prefetch_related(
            Prefetch(
                "pet_pet_contact_links",
                queryset=(
                    Pet_Contact_Link.objects.select_related(
                        "center_contact"
                    )
                    .filter(
                        is_active=True,
                        center_contact__is_active=True,
                    )
                    .order_by(
                        "role",
                        "-is_primary_contact",
                        "center_contact__last_name",
                        "center_contact__first_name",
                        "center_contact__institution_name",
                    )
                ),
                to_attr="prefetched_pet_contact_links",
            )
        )
    )


def _normalize_search_type(search_type: Optional[str]) -> str:
    return (search_type or "").strip().lower()


def _normalize_query(query: Optional[str]) -> str:
    return (query or "").strip()


def _apply_search_filter(
    *,
    qs: QuerySet[Pet],
    search_type: str,
    query: str,
) -> QuerySet[Pet]:
    if search_type in {"", "all", "general", "pet"}:
        return qs.filter(_general_search_q(query))

    if search_type in {"name", "pet_name"}:
        return qs.filter(name__icontains=query)

    if search_type in {"history", "history_code", "clinical_history"}:
        return qs.filter(history_code__icontains=query)

    if search_type == "species":
        return qs.filter(species__global_species__name__icontains=query)

    if search_type == "breed":
        return qs.filter(breed__global_breed__name__icontains=query)

    if search_type == "microchip":
        return qs.filter(microchip_code__icontains=query)

    if search_type in {"status", "pet_status"}:
        return qs.filter(status__icontains=query)

    if search_type in {"clinical_record_status", "record_status"}:
        return qs.filter(clinical_record_status__icontains=query)

    if search_type in PET_CONTACT_LINK_TEXT_SEARCH_TYPE_ALIASES:
        return qs.filter(
            _active_pet_contact_link_q()
            & _pet_contact_link_text_q(query)
        )

    if search_type in {"primary", "primary_contact", "main_contact"}:
        return qs.filter(
            _active_pet_contact_link_q()
            & Q(pet_pet_contact_links__is_primary_contact=True)
            & _pet_contact_link_text_q(query)
        )

    if search_type in {
        "emergency",
        "emergency_contact",
        "emergency_contacts",
    }:
        return qs.filter(
            _active_pet_contact_link_q()
            & Q(pet_pet_contact_links__is_emergency_contact=True)
            & _pet_contact_link_text_q(query)
        )

    if search_type in {
        "pickup",
        "pickup_authorized",
        "pickup_authorized_contacts",
    }:
        return qs.filter(
            _active_pet_contact_link_q()
            & Q(pet_pet_contact_links__can_pickup_pet=True)
            & _pet_contact_link_text_q(query)
        )

    role_values = _role_values_for_search_type(search_type)

    if role_values:
        return qs.filter(
            _active_pet_contact_link_q()
            & Q(pet_pet_contact_links__role__in=role_values)
            & _pet_contact_link_text_q(query)
        )

    return qs.filter(_general_search_q(query))


def _general_search_q(query: str) -> Q:
    pet_q = (
        Q(name__icontains=query)
        | Q(history_code__icontains=query)
        | Q(microchip_code__icontains=query)
        | Q(reference__icontains=query)
        | Q(body_description__icontains=query)
        | Q(status__icontains=query)
        | Q(clinical_record_status__icontains=query)
        | Q(species__global_species__name__icontains=query)
        | Q(breed__global_breed__name__icontains=query)
    )

    pet_contact_link_q = (
        _active_pet_contact_link_q()
        & _pet_contact_link_text_q(query)
    )

    return pet_q | pet_contact_link_q


def _active_pet_contact_link_q() -> Q:
    return (
        Q(pet_pet_contact_links__is_active=True)
        & Q(pet_pet_contact_links__center_contact__is_active=True)
    )


def _pet_contact_link_text_q(query: str) -> Q:
    return (
        Q(pet_pet_contact_links__center_contact__first_name__icontains=query)
        | Q(pet_pet_contact_links__center_contact__last_name__icontains=query)
        | Q(
            pet_pet_contact_links__center_contact__institution_name__icontains=query
        )
        | Q(pet_pet_contact_links__center_contact__document_id__icontains=query)
        | Q(pet_pet_contact_links__center_contact__email__icontains=query)
        | Q(
            pet_pet_contact_links__center_contact__primary_phone__icontains=query
        )
        | Q(
            pet_pet_contact_links__center_contact__secondary_phone__icontains=query
        )
        | Q(
            pet_pet_contact_links__center_contact__tertiary_phone__icontains=query
        )
        | Q(pet_pet_contact_links__specific_relationship__icontains=query)
        | Q(pet_pet_contact_links__notes__icontains=query)
    )


def _role_values_for_search_type(search_type: str) -> list[str]:
    role_map: dict[str, list[str]] = {
        "owner": [Role.OWNER_GUARDIAN.value],
        "owners": [Role.OWNER_GUARDIAN.value],
        "guardian": [Role.OWNER_GUARDIAN.value],
        "guardians": [Role.OWNER_GUARDIAN.value],
        "owner_guardian": [Role.OWNER_GUARDIAN.value],
        "owner_guardians": [Role.OWNER_GUARDIAN.value],

        "caregiver": [Role.CAREGIVER.value],
        "caregivers": [Role.CAREGIVER.value],

        "billing": [Role.BILLING_RESPONSIBLE.value],
        "billing_responsible": [Role.BILLING_RESPONSIBLE.value],
        "billing_responsibles": [Role.BILLING_RESPONSIBLE.value],

        "referring_vet": [Role.REFERRING_VET.value],
        "referring_vets": [Role.REFERRING_VET.value],

        "institution": [Role.RESPONSIBLE_INSTITUTION.value],
        "responsible_institution": [Role.RESPONSIBLE_INSTITUTION.value],
        "responsible_institutions": [Role.RESPONSIBLE_INSTITUTION.value],

        "referring_institution": [Role.REFERRING_INSTITUTION.value],
        "referring_institutions": [Role.REFERRING_INSTITUTION.value],

        "breeder": [Role.BREEDER.value],
        "breeders": [Role.BREEDER.value],

        "shelter": [Role.SHELTER_OR_FOUNDATION.value],
        "shelters": [Role.SHELTER_OR_FOUNDATION.value],
        "foundation": [Role.SHELTER_OR_FOUNDATION.value],
        "foundations": [Role.SHELTER_OR_FOUNDATION.value],
        "shelter_or_foundation": [Role.SHELTER_OR_FOUNDATION.value],
        "shelters_or_foundations": [Role.SHELTER_OR_FOUNDATION.value],
    }

    return role_map.get(search_type, [])