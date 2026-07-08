# api/application/pet/dto/Pet_Data_DTO.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SexCode = Literal["m", "f", "u"]


@dataclass(frozen=True)
class Species_In_Center_DTO:
    id: int
    name: str


@dataclass(frozen=True)
class Breed_For_Species_In_Center_DTO:
    id: int
    name: str


@dataclass(frozen=True)
class Center_Staff_Membership_DTO:
    id: int
    name: str


@dataclass(frozen=True)
class Veterinary_Center_DTO:
    id: int
    name: str


@dataclass(frozen=True)
class Center_Contact_Summary_DTO:
    id: int
    center_contact_type: str
    display_name: Optional[str]

    first_name: Optional[str]
    last_name: Optional[str]
    institution_name: Optional[str]

    document_id: Optional[str]
    email: Optional[str]

    primary_phone: Optional[str]
    secondary_phone: Optional[str]
    tertiary_phone: Optional[str]

    address: Optional[str]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]

    notes: Optional[str]
    is_active: bool


@dataclass(frozen=True)
class Pet_Contact_Link_DTO:
    id: int

    role: str
    role_label: str
    specific_relationship: Optional[str]

    is_primary_contact: bool
    is_emergency_contact: bool

    can_authorize_treatment: bool
    can_receive_medical_updates: bool
    can_receive_billing: bool
    can_pickup_pet: bool

    notes: Optional[str]
    is_active: bool

    center_contact: Center_Contact_Summary_DTO


@dataclass(frozen=True)
class Pet_Data_DTO:
    id: int
    history_code: str
    name: str

    sex: SexCode
    sex_label: str

    species: Species_In_Center_DTO
    breed: Optional[Breed_For_Species_In_Center_DTO]

    sterilized: bool
    birth_date: Optional[str]
    body_description: Optional[str]
    size: Optional[str]
    last_weight: Optional[float]

    # Internal center veterinarian.
    #
    # This points to Center_Staff_Membership.
    # It is None when the pet was attended by an external veterinarian.
    last_attending_vet: Optional[Center_Staff_Membership_DTO]

    # External veterinarian name.
    #
    # This is used when the attending veterinarian is not part of the center staff.
    # In that case, last_attending_vet should normally be None.
    last_attending_vet_external_name: Optional[str]

    reference: Optional[str]

    has_pedigree: bool
    pedigree_registry: Optional[str]

    has_visual_identification: bool
    visual_tag: Optional[str]
    visual_identification_or_tattoo_description: Optional[str]

    has_microchip: bool
    microchip_code: Optional[str]
    microchip_date: Optional[str]
    microchip_body_region: Optional[str]

    clinical_observations: Optional[str]
    internal_notes: Optional[str]
    photo_url: Optional[str]

    veterinary_center: Optional[Veterinary_Center_DTO]

    status: Optional[str]
    inactive_at: Optional[str]
    deceased_at: Optional[str]
    archived_at: Optional[str]
    clinical_record_status: Optional[str]

    # All pet-contact-link relations.
    contact_links: list[Pet_Contact_Link_DTO]

    # Role-based pet-contact-link groups.
    owner_guardians: list[Pet_Contact_Link_DTO]
    caregivers: list[Pet_Contact_Link_DTO]
    billing_responsibles: list[Pet_Contact_Link_DTO]
    referring_vets: list[Pet_Contact_Link_DTO]
    responsible_institutions: list[Pet_Contact_Link_DTO]
    referring_institutions: list[Pet_Contact_Link_DTO]
    breeders: list[Pet_Contact_Link_DTO]
    shelters_or_foundations: list[Pet_Contact_Link_DTO]

    # Permission/flag-based pet-contact-link groups.
    emergency_contacts: list[Pet_Contact_Link_DTO]
    pickup_authorized_contacts: list[Pet_Contact_Link_DTO]
    treatment_authorization_contacts: list[Pet_Contact_Link_DTO]
    medical_update_contacts: list[Pet_Contact_Link_DTO]
    billing_update_contacts: list[Pet_Contact_Link_DTO]