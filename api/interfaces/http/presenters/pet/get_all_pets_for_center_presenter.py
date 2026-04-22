# api/interfaces/http/presenters/pet/search_pets_presenter.py

from typing import Any

from api.application.pet.dto.get_all_pets_for_center_dto import Get_All_Pets_For_Center_DTO


def present_all_pets_for_center_pet(dto: Get_All_Pets_For_Center_DTO) -> dict[str, Any]:
    return {
        "id": dto.id,
        "name": dto.name,
        "species": dto.species,
        "breed": dto.breed,
        "sex": dto.sex,
        "birth_date": (
            dto.birth_date.isoformat()
            if dto.birth_date else None
        ),
        "sterilized": dto.sterilized,
        "has_microchip": dto.has_microchip,
        "photo_url": dto.photo_url,
        "description": dto.description,
        "history_code": dto.history_code,
        "owner_names": dto.owner_names,
        "responsible_names": dto.responsible_names,
        "veterinary_center_id": dto.veterinary_center_id,
    }


def present_search_pets_list(
    results: list[Get_All_Pets_For_Center_DTO],
) -> list[dict[str, Any]]:
    return [
        present_all_pets_for_center_pet(dto)
        for dto in results
    ]