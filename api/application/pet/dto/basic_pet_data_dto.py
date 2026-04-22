# api/application/pet/dto/basic_pet_data_dto.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional


SexCode = Literal["m", "f", "u"]


CONTACT_ROLE_LABELS: dict[str, str] = {
    "OWNER": "Dueño",
    "RESPONSIBLE": "Responsable",
    "AUTHORIZED": "Autorizado",
    "EMERGENCY": "Emergencia",
    "BREEDER": "Criador",
}


@dataclass(frozen=True, slots=True)
class SpeciesDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class BreedDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class CenterPersonnelDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class VeterinaryCenterDTO:
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class PetContactDTO:
    id: int
    contact_id: int
    name: str
    relationship: Optional[str]
    role: str
    role_label: str
    is_primary_contact: bool


@dataclass(frozen=True, slots=True)
class BasicPetDataDTO:
    id: int
    history_code: str
    name: str
    sex: SexCode
    sex_label: str
    species: SpeciesDTO
    breed: Optional[BreedDTO]
    sterilized: bool
    birth_date: Optional[str]
    body_description: Optional[str]
    size: Optional[str]
    last_weight: Optional[float]
    last_attending_vet: Optional[CenterPersonnelDTO]
    reference: Optional[str]
    has_pedigree: bool
    pedigree_registry: Optional[str]
    has_visual_identification: bool
    visual_id_tag: Optional[str]
    visual_id_tattoo_description: Optional[str]
    has_microchip: bool
    microchip_code: Optional[str]
    microchip_date: Optional[str]
    microchip_region: Optional[str]
    observations: Optional[str]
    notes: Optional[str]
    photo_url: Optional[str]
    veterinary_center: Optional[VeterinaryCenterDTO]
    status: Optional[str]
    inactive_at: Optional[str]
    deceased_at: Optional[str]
    archived_at: Optional[str]
    clinical_record_status: Optional[str]
    contacts: list[PetContactDTO]
    owners: list[PetContactDTO]
    responsible: Optional[PetContactDTO]
    authorized: list[PetContactDTO]
    emergency: list[PetContactDTO]
    breeder: list[PetContactDTO]

    @classmethod
    def from_model(cls, pet: Any) -> "BasicPetDataDTO":
        """
        `pet` is typed as Any on purpose.

        This avoids Pylance false positives with Django model dynamic attributes
        such as:
        - get_<field>_display()
        - related objects
        - dynamically generated FK attributes
        """

        species_obj = getattr(pet, "species", None)
        breed_obj = getattr(pet, "breed", None)
        vet_obj = getattr(pet, "last_attending_vet", None)
        center_obj = getattr(pet, "veterinary_center", None)

        contacts, owners, responsible, authorized, emergency, breeder = (
            cls._build_contacts_from_pet(pet)
        )

        return cls(
            id=int(getattr(pet, "id")),
            history_code=str(getattr(pet, "history_code")),
            name=str(getattr(pet, "name")),
            sex=cls._normalize_sex(getattr(pet, "sex", "u")),
            sex_label=cls._get_display_value(
                instance=pet,
                display_method_name="get_sex_display",
                fallback=str(getattr(pet, "sex", "u")),
            ),
            species=SpeciesDTO(
                id=int(getattr(species_obj, "id")),
                name=str(getattr(species_obj, "name")),
            ),
            breed=(
                BreedDTO(
                    id=int(getattr(breed_obj, "id")),
                    name=str(getattr(breed_obj, "name")),
                )
                if breed_obj is not None
                else None
            ),
            sterilized=bool(getattr(pet, "sterilized", False)),
            birth_date=cls._to_iso_date(getattr(pet, "birth_date", None)),
            body_description=cls._none_if_blank(getattr(pet, "body_description", None)),
            size=cls._none_if_blank(getattr(pet, "size", None)),
            last_weight=cls._to_float_or_none(getattr(pet, "last_weight", None)),
            last_attending_vet=(
                CenterPersonnelDTO(
                    id=int(getattr(vet_obj, "id")),
                    name=cls._get_person_name(vet_obj),
                )
                if vet_obj is not None
                else None
            ),
            reference=cls._none_if_blank(getattr(pet, "reference", None)),
            has_pedigree=bool(getattr(pet, "has_pedigree", False)),
            pedigree_registry=cls._none_if_blank(
                getattr(pet, "pedigree_registry", None)
            ),
            has_visual_identification=bool(
                getattr(pet, "has_visual_identification", False)
            ),
            visual_id_tag=cls._none_if_blank(getattr(pet, "visual_id_tag", None)),
            visual_id_tattoo_description=cls._none_if_blank(
                getattr(pet, "visual_id_tattoo_description", None)
            ),
            has_microchip=bool(getattr(pet, "has_microchip", False)),
            microchip_code=cls._none_if_blank(getattr(pet, "microchip_code", None)),
            microchip_date=cls._to_iso_date(getattr(pet, "microchip_date", None)),
            microchip_region=cls._none_if_blank(
                getattr(pet, "microchip_region", None)
            ),
            observations=cls._none_if_blank(getattr(pet, "observations", None)),
            notes=cls._none_if_blank(getattr(pet, "notes", None)),
            photo_url=cls._none_if_blank(getattr(pet, "photo_url", None)),
            veterinary_center=(
                VeterinaryCenterDTO(
                    id=int(getattr(center_obj, "id")),
                    name=str(getattr(center_obj, "name")),
                )
                if center_obj is not None
                else None
            ),
            status=cls._none_if_blank(
                cls._get_display_value(
                    instance=pet,
                    display_method_name="get_status_display",
                    fallback=getattr(pet, "status", None),
                )
            ),
            inactive_at=cls._to_iso_datetime(getattr(pet, "inactive_at", None)),
            deceased_at=cls._to_iso_datetime(getattr(pet, "deceased_at", None)),
            archived_at=cls._to_iso_datetime(getattr(pet, "archived_at", None)),
            clinical_record_status=cls._none_if_blank(
                cls._get_display_value(
                    instance=pet,
                    display_method_name="get_clinical_record_status_display",
                    fallback=getattr(pet, "clinical_record_status", None),
                )
            ),
            contacts=contacts,
            owners=owners,
            responsible=responsible,
            authorized=authorized,
            emergency=emergency,
            breeder=breeder,
        )

    @classmethod
    def _build_contacts_from_pet(
        cls,
        pet: Any,
    ) -> tuple[
        list[PetContactDTO],
        list[PetContactDTO],
        Optional[PetContactDTO],
        list[PetContactDTO],
        list[PetContactDTO],
        list[PetContactDTO],
    ]:
        contact_manager = (
            getattr(pet, "pet_contacts", None)
            or getattr(pet, "pet_contact_set", None)
        )

        if contact_manager is None:
            return [], [], None, [], [], []

        try:
            pet_contacts = list(contact_manager.select_related("contact").all())
        except Exception:
            pet_contacts = list(contact_manager.all())

        contacts: list[PetContactDTO] = []
        owners: list[PetContactDTO] = []
        responsible: Optional[PetContactDTO] = None
        authorized: list[PetContactDTO] = []
        emergency: list[PetContactDTO] = []
        breeder: list[PetContactDTO] = []

        for pc in pet_contacts:
            dto = cls._build_contact_dto(pc)
            contacts.append(dto)

            role_code = dto.role

            if role_code == "OWNER":
                owners.append(dto)
            elif role_code == "RESPONSIBLE":
                if dto.is_primary_contact or responsible is None:
                    responsible = dto
            elif role_code == "AUTHORIZED":
                authorized.append(dto)
            elif role_code == "EMERGENCY":
                emergency.append(dto)
            elif role_code == "BREEDER":
                breeder.append(dto)

        return contacts, owners, responsible, authorized, emergency, breeder

    @classmethod
    def _build_contact_dto(cls, pet_contact: Any) -> PetContactDTO:
        contact_obj = getattr(pet_contact, "contact", None)

        role_code = cls._normalize_choice_code(getattr(pet_contact, "role", None))
        role_label = cls._get_display_value(
            instance=pet_contact,
            display_method_name="get_role_display",
            fallback=CONTACT_ROLE_LABELS.get(role_code, role_code),
        )

        return PetContactDTO(
            id=int(getattr(pet_contact, "id")),
            contact_id=int(getattr(contact_obj, "id")),
            name=cls._get_contact_name(contact_obj),
            relationship=cls._none_if_blank(
                getattr(pet_contact, "relationship", None)
            ),
            role=role_code,
            role_label=str(role_label),
            is_primary_contact=bool(
                getattr(pet_contact, "is_primary_contact", False)
            ),
        )

    @staticmethod
    def _normalize_sex(value: Any) -> SexCode:
        sex = str(value).lower().strip()
        if sex in {"m", "f", "u"}:
            return sex  # type: ignore[return-value]
        return "u"

    @staticmethod
    def _normalize_choice_code(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, tuple) and len(value) >= 1:
            return str(value[0]).strip()

        return str(value).strip()

    @staticmethod
    def _get_display_value(
        *,
        instance: Any,
        display_method_name: str,
        fallback: Any,
    ) -> str:
        method = getattr(instance, display_method_name, None)
        if callable(method):
            try:
                value = method()
                return "" if value is None else str(value)
            except Exception:
                pass

        return "" if fallback is None else str(fallback)

    @staticmethod
    def _get_person_name(person: Any) -> str:
        for attr_name in ("full_name", "name"):
            value = getattr(person, attr_name, None)
            if value:
                return str(value)

        first_name = getattr(person, "first_name", None)
        last_name = getattr(person, "last_name", None)
        combined = " ".join(
            part.strip()
            for part in [str(first_name or "").strip(), str(last_name or "").strip()]
            if part and str(part).strip()
        )
        if combined:
            return combined

        return ""

    @staticmethod
    def _get_contact_name(contact: Any) -> str:
        for attr_name in ("name", "full_name", "institution_name"):
            value = getattr(contact, attr_name, None)
            if value:
                return str(value)

        first_name = getattr(contact, "first_name", None)
        last_name = getattr(contact, "last_name", None)
        combined = " ".join(
            part.strip()
            for part in [str(first_name or "").strip(), str(last_name or "").strip()]
            if part and str(part).strip()
        )
        if combined:
            return combined

        return ""

    @staticmethod
    def _none_if_blank(value: Any) -> Optional[str]:
        if value is None:
            return None

        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _to_float_or_none(value: Any) -> Optional[float]:
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

    @staticmethod
    def _to_iso_date(value: Any) -> Optional[str]:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date().isoformat()

        if isinstance(value, date):
            return value.isoformat()

        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _to_iso_datetime(value: Any) -> Optional[str]:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        text = str(value).strip()
        return text if text else None