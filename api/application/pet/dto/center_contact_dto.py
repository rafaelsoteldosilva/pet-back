# api/application/pet/dto/center_contact_dto.py

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Center_Contact_DTO:
    id: int
    center_contact_type: str

    display_name: str | None

    first_name: str | None
    last_name: str | None
    institution_name: str | None

    document_id: str | None
    email: str | None

    primary_phone: str | None
    secondary_phone: str | None
    tertiary_phone: str | None
    address: str | None
    city: str | None
    region: str | None
    country: str | None

    notes: str | None
    is_active: bool