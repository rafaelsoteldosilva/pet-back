# api/interfaces/http/presenters/pet/pet_data_presenter.py

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from api.application.pet.dto.pet_data_dto import (
    Pet_Data_DTO,
)


JsonDict = dict[str, Any]


def pet_data_presenter(
    dto: Pet_Data_DTO,
) -> JsonDict:
    """
    Presents Pet_Data_DTO as a JSON-serializable dictionary.

    This presenter must not query ORM models or apply business/application rules.
    The query layer is responsible for building the DTO.
    The presenter only converts the DTO into the HTTP response shape.

    Because Pet_Data_DTO is a dataclass, asdict(dto) also converts nested
    dataclasses and lists into plain dictionaries/lists.
    """

    return asdict(dto)


__all__ = [
    "pet_data_presenter",
]