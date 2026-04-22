# api/application/pet/queries/get_basic_pet_data.py

from api.application.pet.dto.basic_pet_data_dto import BasicPetDataDTO
from api.infrastructure.orm.models.pet import Pet


def get_basic_pet_data(
    *,
    center_id: int,
    pet_id: int,
) -> BasicPetDataDTO | None:

    pet = (
        Pet.objects
        .filter(
            id=pet_id,
            veterinary_center_id=center_id,
        )
        .select_related(
            "species",
            "breed",
            "last_attending_vet",
            "veterinary_center",
        )
        .prefetch_related(
            "pet_contacts__contact",
        )
        .first()
    )

    if not pet:
        return None

    return BasicPetDataDTO.from_model(pet)