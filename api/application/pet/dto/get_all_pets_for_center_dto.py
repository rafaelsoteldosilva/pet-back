# api/application/pet/dto/get_all_pets_for_center_pets_dto.py

from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class Get_All_Pets_For_Center_DTO:
    """
    DTO used by Get_All_Pets_For_Center query.
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

    history_code: Optional[str]

    owner_names: List[str]
    responsible_names: List[str]

    veterinary_center_id: int