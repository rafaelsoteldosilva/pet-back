# api/infrastructure/repositories/django_pet_repository.py

from api.infrastructure.orm.models.pet import Pet


class Pet_Repository:

    @staticmethod
    def get_by_id(pet_id: int) -> Pet | None:
        return Pet.objects.filter(id=pet_id).first()

    @staticmethod
    def save(pet: Pet) -> Pet:
        pet.save()
        return pet
