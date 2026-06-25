# api/application/pet/dto/all_pets_for_center_pets_dto.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class All_Pets_For_Center_DTO:
    """ 
    DTO used by the Get_All_Pets_For_Center query.

    This DTO is intentionally flattened for list/search views.
    Contact names are display values derived from Pet_Contact_Link rows and
    their related Center_Contact records.
    """

    id: int
    name: str
    species: str
    breed: Optional[str]

    sex: str
    birth_date: Optional[date]

    sterilized: bool
    has_microchip: bool

    photo_url: Optional[str]
    description: Optional[str]

    history_code: str

    owner_guardian_names: list[str]
    primary_contact_names: list[str]

    veterinary_center_id: int