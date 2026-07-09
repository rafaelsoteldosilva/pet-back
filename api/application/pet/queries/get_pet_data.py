# api/application/pet/queries/get_pet_data.py

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, NamedTuple, Optional, cast

from django.db.models import Prefetch
from rest_framework.exceptions import NotFound

from api.application.pet.dto.pet_data_dto import (
    Breed_For_Species_In_Center_DTO,
    Center_Contact_Summary_DTO,
    Center_Staff_Member_DTO,
    Pet_Contact_Link_DTO,
    Pet_Data_DTO,
    SexCode,
    Species_In_Center_DTO,
    Veterinary_Center_DTO,
)
from api.infrastructure.orm.models.center import Center_Contact
from api.infrastructure.orm.models.pet import Pet, Pet_Contact_Link
from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Pet_Contact_Link_Role,
)
from api.shared.constants.constants import (
    BREED_IN_CENTER_MODEL,
    CENTER_CONTACT_MODEL,
    CENTER_STAFF_MEMBER_MODEL,
    PET_CONTACT_LINK_MODEL,
    PET_MODEL,
    SPECIES_IN_CENTER_MODEL,
    VETERINARY_CENTER_MODEL,
)


Role = Choices_Pet_Contact_Link_Role
CenterContactType = Choices_Center_Contact_Type


class PetContactLinkGroups(NamedTuple):
    contact_links: list[Pet_Contact_Link_DTO]

    owner_guardians: list[Pet_Contact_Link_DTO]
    caregivers: list[Pet_Contact_Link_DTO]
    billing_responsibles: list[Pet_Contact_Link_DTO]
    referring_vets: list[Pet_Contact_Link_DTO]
    responsible_institutions: list[Pet_Contact_Link_DTO]
    referring_institutions: list[Pet_Contact_Link_DTO]
    breeders: list[Pet_Contact_Link_DTO]
    shelters_or_foundations: list[Pet_Contact_Link_DTO]

    emergency_contacts: list[Pet_Contact_Link_DTO]
    pickup_authorized_contacts: list[Pet_Contact_Link_DTO]
    treatment_authorization_contacts: list[Pet_Contact_Link_DTO]
    medical_update_contacts: list[Pet_Contact_Link_DTO]
    billing_update_contacts: list[Pet_Contact_Link_DTO]


def get_pet_data(
    *,
    center_id: int,
    pet_id: int,
) -> Pet_Data_DTO:
    """
    Application query for the Pet Data screen.

    Important relationship path:
    - Pet does not directly expose Center_Contact records.
    - Pet exposes Pet_Contact_Link records.
    - Each Pet_Contact_Link points to one Center_Contact.
    """

    pet = _get_pet_with_related_data_or_raise(
        center_id=center_id,
        pet_id=pet_id,
    )

    return from_model(pet)


def _get_pet_with_related_data_or_raise(
    *,
    center_id: int,
    pet_id: int,
) -> Pet:
    try:
        return (
            Pet.objects.select_related(
                "species",
                "species__global_species",
                "breed",
                "breed__global_breed",
                "last_attending_vet",
                "last_attending_vet__user",
                "veterinary_center",
            )
            .prefetch_related(
                Prefetch(
                    "pet_pet_contact_links",
                    queryset=(
                        Pet_Contact_Link.objects.select_related(
                            "center_contact",
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
            .get(
                id=pet_id,
                veterinary_center_id=center_id,
            )
        )
    except Pet.DoesNotExist as exc:
        raise NotFound("Pet not found.") from exc


def from_model(pet: Pet) -> Pet_Data_DTO:
    """
    Builds a Pet_Data_DTO from a Pet ORM model.
    """

    species_obj = getattr(pet, "species", None)
    breed_obj = getattr(pet, "breed", None)
    vet_obj = getattr(pet, "last_attending_vet", None)
    center_obj = getattr(pet, "veterinary_center", None)

    pet_contact_link_groups = _build_contact_links_from_pet(pet)

    return Pet_Data_DTO(
        id=_get_required_int_pk(
            pet,
            model_name=PET_MODEL,
        ),
        history_code=str(getattr(pet, "history_code", "")),
        name=str(getattr(pet, "name", "")),
        sex=_normalize_sex(getattr(pet, "sex", "u")),
        sex_label=_get_display_value(
            instance=pet,
            display_method_name="get_sex_display",
            fallback=getattr(pet, "sex", "u"),
        ),
        species=Species_In_Center_DTO(
            id=_get_required_int_pk(
                species_obj,
                model_name=SPECIES_IN_CENTER_MODEL,
            ),
            name=_get_species_name(species_obj),
        ),
        breed=(
            Breed_For_Species_In_Center_DTO(
                id=_get_required_int_pk(
                    breed_obj,
                    model_name=BREED_IN_CENTER_MODEL,
                ),
                name=_get_breed_name(breed_obj),
            )
            if breed_obj is not None
            else None
        ),
        sterilized=bool(getattr(pet, "sterilized", False)),
        birth_date=_to_iso_date(getattr(pet, "birth_date", None)),
        body_description=_none_if_blank(
            getattr(pet, "body_description", None),
        ),
        size=_none_if_blank(getattr(pet, "size", None)),
        last_weight=_to_float_or_none(getattr(pet, "last_weight", None)),
        last_attending_vet=(
            Center_Staff_Member_DTO(
                id=_get_required_int_pk(
                    vet_obj,
                    model_name=CENTER_STAFF_MEMBER_MODEL,
                ),
                name=_get_person_name(vet_obj),
            )
            if vet_obj is not None
            else None
        ),
        last_attending_vet_external_name=_none_if_blank(
            getattr(pet, "last_attending_vet_external_name", None),
        ),
        reference=_none_if_blank(getattr(pet, "reference", None)),
        has_pedigree=bool(getattr(pet, "has_pedigree", False)),
        pedigree_registry=_none_if_blank(
            getattr(pet, "pedigree_registry", None),
        ),
        has_visual_identification=bool(
            getattr(pet, "has_visual_identification", False),
        ),
        visual_tag=_none_if_blank(getattr(pet, "visual_tag", None)),
        visual_identification_or_tattoo_description=_none_if_blank(
            getattr(
                pet,
                "visual_identification_or_tattoo_description",
                None,
            ),
        ),
        has_microchip=bool(getattr(pet, "has_microchip", False)),
        microchip_code=_none_if_blank(getattr(pet, "microchip_code", None)),
        microchip_date=_to_iso_date(getattr(pet, "microchip_date", None)),
        microchip_body_region=_none_if_blank(
            getattr(pet, "microchip_body_region", None),
        ),
        clinical_observations=_none_if_blank(
            getattr(pet, "clinical_observations", None),
        ),
        internal_notes=_none_if_blank(getattr(pet, "internal_notes", None)),
        photo_url=_none_if_blank(getattr(pet, "photo_url", None)),
        veterinary_center=(
            Veterinary_Center_DTO(
                id=_get_required_int_pk(
                    center_obj,
                    model_name=VETERINARY_CENTER_MODEL,
                ),
                name=str(getattr(center_obj, "name", "")),
            )
            if center_obj is not None
            else None
        ),
        status=_none_if_blank(
            _get_display_value(
                instance=pet,
                display_method_name="get_status_display",
                fallback=getattr(pet, "status", None),
            ),
        ),
        inactive_at=_to_iso_datetime(getattr(pet, "inactive_at", None)),
        deceased_at=_to_iso_datetime(getattr(pet, "deceased_at", None)),
        archived_at=_to_iso_datetime(getattr(pet, "archived_at", None)),
        clinical_record_status=_none_if_blank(
            _get_display_value(
                instance=pet,
                display_method_name="get_clinical_record_status_display",
                fallback=getattr(pet, "clinical_record_status", None),
            ),
        ),
        contact_links=pet_contact_link_groups.contact_links,
        owner_guardians=pet_contact_link_groups.owner_guardians,
        caregivers=pet_contact_link_groups.caregivers,
        billing_responsibles=pet_contact_link_groups.billing_responsibles,
        referring_vets=pet_contact_link_groups.referring_vets,
        responsible_institutions=(
            pet_contact_link_groups.responsible_institutions
        ),
        referring_institutions=(
            pet_contact_link_groups.referring_institutions
        ),
        breeders=pet_contact_link_groups.breeders,
        shelters_or_foundations=(
            pet_contact_link_groups.shelters_or_foundations
        ),
        emergency_contacts=pet_contact_link_groups.emergency_contacts,
        pickup_authorized_contacts=(
            pet_contact_link_groups.pickup_authorized_contacts
        ),
        treatment_authorization_contacts=(
            pet_contact_link_groups.treatment_authorization_contacts
        ),
        medical_update_contacts=(
            pet_contact_link_groups.medical_update_contacts
        ),
        billing_update_contacts=pet_contact_link_groups.billing_update_contacts,
    )


def _build_contact_links_from_pet(pet: Pet) -> PetContactLinkGroups:
    """
    Builds contact-link DTO groups.

    The source collection is Pet_Contact_Link, not Center_Contact.

    Correct path:
    pet -> pet_pet_contact_links -> Pet_Contact_Link -> center_contact
    """

    pet_contact_links = _get_pet_contact_links_from_pet(pet)

    contact_links: list[Pet_Contact_Link_DTO] = []

    owner_guardians: list[Pet_Contact_Link_DTO] = []
    caregivers: list[Pet_Contact_Link_DTO] = []
    billing_responsibles: list[Pet_Contact_Link_DTO] = []
    referring_vets: list[Pet_Contact_Link_DTO] = []
    responsible_institutions: list[Pet_Contact_Link_DTO] = []
    referring_institutions: list[Pet_Contact_Link_DTO] = []
    breeders: list[Pet_Contact_Link_DTO] = []
    shelters_or_foundations: list[Pet_Contact_Link_DTO] = []

    emergency_contacts: list[Pet_Contact_Link_DTO] = []
    pickup_authorized_contacts: list[Pet_Contact_Link_DTO] = []
    treatment_authorization_contacts: list[Pet_Contact_Link_DTO] = []
    medical_update_contacts: list[Pet_Contact_Link_DTO] = []
    billing_update_contacts: list[Pet_Contact_Link_DTO] = []

    for pet_contact_link in pet_contact_links:
        dto = _build_pet_contact_link_dto(pet_contact_link)

        contact_links.append(dto)

        role_code = dto.role.strip().upper()

        if role_code == Role.OWNER_GUARDIAN.value:
            owner_guardians.append(dto)

        elif role_code == Role.CAREGIVER.value:
            caregivers.append(dto)

        elif role_code == Role.BILLING_RESPONSIBLE.value:
            billing_responsibles.append(dto)

        elif role_code == Role.REFERRING_VET.value:
            referring_vets.append(dto)

        elif role_code == Role.RESPONSIBLE_INSTITUTION.value:
            responsible_institutions.append(dto)

        elif role_code == Role.REFERRING_INSTITUTION.value:
            referring_institutions.append(dto)

        elif role_code == Role.BREEDER.value:
            breeders.append(dto)

        elif role_code == Role.SHELTER_OR_FOUNDATION.value:
            shelters_or_foundations.append(dto)

        if dto.is_emergency_contact:
            emergency_contacts.append(dto)

        if dto.can_pickup_pet:
            pickup_authorized_contacts.append(dto)

        if dto.can_authorize_treatment:
            treatment_authorization_contacts.append(dto)

        if dto.can_receive_medical_updates:
            medical_update_contacts.append(dto)

        if dto.can_receive_billing:
            billing_update_contacts.append(dto)

    return PetContactLinkGroups(
        contact_links=contact_links,
        owner_guardians=owner_guardians,
        caregivers=caregivers,
        billing_responsibles=billing_responsibles,
        referring_vets=referring_vets,
        responsible_institutions=responsible_institutions,
        referring_institutions=referring_institutions,
        breeders=breeders,
        shelters_or_foundations=shelters_or_foundations,
        emergency_contacts=emergency_contacts,
        pickup_authorized_contacts=pickup_authorized_contacts,
        treatment_authorization_contacts=treatment_authorization_contacts,
        medical_update_contacts=medical_update_contacts,
        billing_update_contacts=billing_update_contacts,
    )


def _get_pet_contact_links_from_pet(pet: Pet) -> list[Pet_Contact_Link]:
    """
    Gets the Pet_Contact_Link records associated with this pet.

    Prefer prefetched links when available.
    Falls back to a direct query when the pet was not prefetched.
    """

    prefetched_pet_contact_links = getattr(
        pet,
        "prefetched_pet_contact_links",
        None,
    )

    if prefetched_pet_contact_links is not None:
        return list(
            cast(
                Iterable[Pet_Contact_Link],
                prefetched_pet_contact_links,
            )
        )

    pet_id = _get_required_int_pk(
        pet,
        model_name=PET_MODEL,
    )

    return list(
        Pet_Contact_Link.objects.select_related(
            "center_contact",
        )
        .filter(
            pet_id=pet_id,
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
    )


def _get_center_contact_from_pet_contact_link(
    pet_contact_link: Pet_Contact_Link,
) -> Center_Contact:
    """
    Extracts the real Center_Contact from the Pet_Contact_Link.

    Correct path:
    Pet_Contact_Link.center_contact
    """

    center_contact_obj = getattr(
        pet_contact_link,
        "center_contact",
        None,
    )

    if center_contact_obj is None:
        raise ValueError(
            "Pet_Contact_Link must have a related Center_Contact before mapping."
        )

    return cast(Center_Contact, center_contact_obj)


def _build_pet_contact_link_dto(
    pet_contact_link: Pet_Contact_Link,
) -> Pet_Contact_Link_DTO:
    """
    Builds a link DTO.

    Link fields come from Pet_Contact_Link.
    Real contact fields come from Pet_Contact_Link.center_contact.
    """

    center_contact_obj = _get_center_contact_from_pet_contact_link(
        pet_contact_link,
    )

    return Pet_Contact_Link_DTO(
        id=_get_required_int_pk(
            pet_contact_link,
            model_name=PET_CONTACT_LINK_MODEL,
        ),
        role=_normalize_choice_code(pet_contact_link.role),
        role_label=_get_pet_contact_link_role_label(pet_contact_link.role),
        specific_relationship=_none_if_blank(
            pet_contact_link.specific_relationship,
        ),
        is_primary_contact=bool(pet_contact_link.is_primary_contact),
        is_emergency_contact=bool(pet_contact_link.is_emergency_contact),
        can_authorize_treatment=bool(pet_contact_link.can_authorize_treatment),
        can_receive_medical_updates=bool(
            pet_contact_link.can_receive_medical_updates,
        ),
        can_receive_billing=bool(pet_contact_link.can_receive_billing),
        can_pickup_pet=bool(pet_contact_link.can_pickup_pet),
        notes=_none_if_blank(pet_contact_link.notes),
        is_active=bool(pet_contact_link.is_active),
        center_contact=_build_center_contact_summary_dto(
            center_contact_obj,
        ),
    )


def _build_center_contact_summary_dto(
    center_contact: Center_Contact,
) -> Center_Contact_Summary_DTO:
    """
    Builds the nested Center_Contact summary DTO.
    """

    return Center_Contact_Summary_DTO(
        id=_get_required_int_pk(
            center_contact,
            model_name=CENTER_CONTACT_MODEL,
        ),
        center_contact_type=str(center_contact.center_contact_type),
        display_name=_build_center_contact_display_name(
            center_contact,
        ),
        first_name=_none_if_blank(center_contact.first_name),
        last_name=_none_if_blank(center_contact.last_name),
        institution_name=_none_if_blank(center_contact.institution_name),
        document_id=_none_if_blank(center_contact.document_id),
        email=_none_if_blank(center_contact.email),
        primary_phone=_none_if_blank(center_contact.primary_phone),
        secondary_phone=_none_if_blank(center_contact.secondary_phone),
        tertiary_phone=_none_if_blank(center_contact.tertiary_phone),
        address=_none_if_blank(center_contact.address),
        city=_none_if_blank(center_contact.city),
        region=_none_if_blank(center_contact.region),
        country=_none_if_blank(center_contact.country),
        notes=_none_if_blank(center_contact.notes),
        is_active=bool(center_contact.is_active),
    )


def _build_center_contact_display_name(
    center_contact: Center_Contact,
) -> Optional[str]:
    center_contact_type = str(center_contact.center_contact_type).upper()

    if center_contact_type == CenterContactType.INSTITUTION.value:
        return _none_if_blank(center_contact.institution_name)

    first_name = _none_if_blank(center_contact.first_name)
    last_name = _none_if_blank(center_contact.last_name)

    display_name = " ".join(
        item for item in (first_name, last_name) if item
    ).strip()

    return display_name or None


def _normalize_sex(value: object | None) -> SexCode:
    sex = str(value or "u").lower().strip()

    if sex in {"m", "f", "u"}:
        return cast(SexCode, sex)

    return "u"


def _normalize_choice_code(value: object | None) -> str:
    if value is None:
        return ""

    if isinstance(value, tuple) and len(value) >= 1:
        return str(value[0]).strip()

    return str(value).strip()


def _get_pet_contact_link_role_label(role: object | None) -> str:
    role_code = _normalize_choice_code(role).upper()

    try:
        return str(Role(role_code).label)
    except ValueError:
        return role_code


def _get_display_value(
    *,
    instance: object,
    display_method_name: str,
    fallback: object | None,
) -> str:
    method = getattr(instance, display_method_name, None)

    if callable(method):
        try:
            value = cast(Callable[[], object | None], method)()
            return "" if value is None else str(value)
        except Exception:
            pass

    return "" if fallback is None else str(fallback)


def _get_species_name(species_obj: object | None) -> str:
    """
    Supports both:
    - species.name
    - species.global_species.name
    """

    if species_obj is None:
        return ""

    name = getattr(species_obj, "name", None)

    if name:
        return str(name)

    global_species = getattr(species_obj, "global_species", None)

    if global_species is not None:
        global_name = getattr(global_species, "name", None)

        if global_name:
            return str(global_name)

    return ""


def _get_breed_name(breed_obj: object | None) -> str:
    """
    Supports both:
    - breed.name
    - breed.global_breed.name
    """

    if breed_obj is None:
        return ""

    name = getattr(breed_obj, "name", None)

    if name:
        return str(name)

    global_breed = getattr(breed_obj, "global_breed", None)

    if global_breed is not None:
        global_name = getattr(global_breed, "name", None)

        if global_name:
            return str(global_name)

    return ""


def _get_person_name(person: object | None) -> str:
    if person is None:
        return ""

    for attr_name in ("full_name", "name"):
        value = getattr(person, attr_name, None)

        if value:
            return str(value)

    first_name = getattr(person, "first_name", None)
    last_name = getattr(person, "last_name", None)

    combined = " ".join(
        part.strip()
        for part in [
            str(first_name or "").strip(),
            str(last_name or "").strip(),
        ]
        if part and str(part).strip()
    )

    if combined:
        return combined

    return ""


def _get_required_int_pk(
    instance: object | None,
    *,
    model_name: str,
) -> int:
    if instance is None:
        raise ValueError(f"{model_name} instance is required.")

    pk = getattr(instance, "pk", None)

    if pk is None:
        raise ValueError(f"{model_name} instance must be saved before mapping.")

    return int(pk)


def _none_if_blank(value: object | None) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()

    return text if text else None


def _to_float_or_none(value: object | None) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, Decimal):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _to_iso_date(value: object | None) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()

    return text if text else None


def _to_iso_datetime(value: object | None) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    text = str(value).strip()

    return text if text else None