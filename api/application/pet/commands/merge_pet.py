# api/application/pet/commands/merge_pet.py

from django.db import transaction
from django.utils import timezone

from api.infrastructure.orm.models import (
    Pet,
    Consultation,
    Pet_Disease_Case,
    Pet_Problem_Case,
)


from api.infrastructure.orm.models.pet import Pet_Contact


@transaction.atomic
def merge_pet(
    *,
    master_pet_id: int,
    secondary_pet_id: int,
    merged_by_id: int,
) -> None:

    master = Pet.objects.select_for_update().get(pk=master_pet_id)
    secondary = Pet.objects.select_for_update().get(pk=secondary_pet_id)

    # master_entity = pet_entity_from_model(master)
    # secondary_entity = pet_entity_from_model(secondary)

    # reglas de dominio
    # merge_pets(master_entity, secondary_entity)

    # mover datos clínicos
    Consultation.objects.filter(pet=secondary).update(pet=master)

    Pet_Disease_Case.objects.filter(pet=secondary).update(pet=master)

    Pet_Problem_Case.objects.filter(pet=secondary).update(pet=master)

    # mover relaciones
    Pet_Contact.objects.filter(pet=secondary).update(pet=master)

    # marcar secondary como merged
    secondary.master_pet_id = master.id
    secondary.status = "ARCHIVED"
    secondary.merged_at = timezone.now()
    secondary.merged_by = merged_by_id

    secondary.save(
        update_fields=[
            "master_pet",
            "status",
            "merged_at",
            "merged_by",
        ]
    )