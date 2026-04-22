# api/application/pet/queries/get_all_pets_for_center.py

from typing import List, Optional
from django.db.models import Q

from api.infrastructure.orm.models.pet import Pet
from api.application.pet.dto.get_all_pets_for_center_dto import Get_All_Pets_For_Center_DTO


def get_all_pets_for_center(
    *,
    veterinary_center_id: int,
    get_all_pets_for_center_type: Optional[str],
    query: Optional[str],
) -> List[Get_All_Pets_For_Center_DTO]:

    qs = (
        Pet.objects
        .filter(veterinary_center_id=veterinary_center_id)
        .select_related(
            "species",
            "breed",
        )
        .prefetch_related(
            "pet_contacts__contact",
        )
    )

    if query:
        query = query.strip()

        if get_all_pets_for_center_type == "name":
            qs = qs.filter(name__icontains=query)

        elif get_all_pets_for_center_type == "history_code":
            qs = qs.filter(history_code__icontains=query)

        elif get_all_pets_for_center_type == "microchip":
            qs = qs.filter(microchip_code__icontains=query)

        elif get_all_pets_for_center_type == "owner":
            qs = qs.filter(
                Q(pet_contacts__role="OWNER") &
                (
                    Q(pet_contacts__contact__first_name__icontains=query) |
                    Q(pet_contacts__contact__last_name__icontains=query) |
                    Q(pet_contacts__contact__institution__icontains=query)
                )
            ).distinct()

        elif get_all_pets_for_center_type == "responsible":
            qs = qs.filter(
                Q(pet_contacts__role="RESPONSIBLE") &
                (
                    Q(pet_contacts__contact__first_name__icontains=query) |
                    Q(pet_contacts__contact__last_name__icontains=query) |
                    Q(pet_contacts__contact__institution__icontains=query)
                )
            ).distinct()

        else:
            # GET ALL PETS FOR CENTER
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(history_code__icontains=query)
                | Q(microchip_code__icontains=query)
                | Q(pet_contacts__contact__first_name__icontains=query)
                | Q(pet_contacts__contact__last_name__icontains=query)
                | Q(pet_contacts__contact__institution__icontains=query)
            ).distinct()

    qs = qs.order_by("name")[:50]

    return [
        Get_All_Pets_For_Center_DTO(
            id=pet.id,
            name=pet.name,
            species=pet.species.name,
            breed=pet.breed.name if pet.breed else None,
            sex=pet.sex,
            birth_date=pet.birth_date,
            sterilized=pet.sterilized,
            has_microchip=pet.has_microchip,
            photo_url=pet.photo_url,
            description=pet.body_description,
            history_code=pet.history_code,
            owner_names=[
                str(pc.contact)
                for pc in pet.pet_contacts.all()
                if pc.role == "OWNER"
            ],
            responsible_names=[
                str(pc.contact)
                for pc in pet.pet_contacts.all()
                if pc.role == "RESPONSIBLE"
            ],
            veterinary_center_id=pet.veterinary_center_id,
        )
        for pet in qs
    ]