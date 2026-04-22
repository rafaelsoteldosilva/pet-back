# api/interfaces/http/presenters/pet/pet_basic_data_presenter.py

from typing import Any

from api.infrastructure.orm.models.pet import Pet


def present_basic_pet_data(pet: Pet) -> dict[str, Any]:
    return {
        "id": pet.id,
        "history_code": pet.history_code,
        "name": pet.name,
        "sex": pet.sex,
        "species": {
            "id": pet.species.id,
            "name": pet.species.name,
        },
        "breed": (
            {
                "id": pet.breed.id,
                "name": pet.breed.name,
            }
            if pet.breed else None
        ),
        "sterilized": pet.sterilized,
        "birth_date": (
            pet.birth_date.isoformat()
            if pet.birth_date else None
        ),
        "body_description": pet.body_description,
        "size": pet.size,
        "last_weight": pet.last_weight,
        "last_attending_vet": (
            {
                "id": pet.last_attending_vet.id,
                "name": str(pet.last_attending_vet),
            }
            if pet.last_attending_vet else None
        ),
        "reference": pet.reference,
        "has_pedigree": pet.has_pedigree,
        "pedigree_registry": pet.pedigree_registry,
        "has_visual_identification": pet.has_visual_identification,
        "visual_id_tag": pet.visual_id_tag,
        "visual_id_tattoo_description": pet.visual_id_tattoo_description,
        "has_microchip": pet.has_microchip,
        "microchip_code": pet.microchip_code,
        "microchip_date": (
            pet.microchip_date.isoformat()
            if pet.microchip_date else None
        ),
        "microchip_region": pet.microchip_region,
        "observations": pet.observations,
        "notes": pet.notes,
        "photo_url": pet.photo_url,
        "contacts": [
            {
                "id": pc.contact.id,
                "role": pc.role,
                "is_primary_contact": pc.is_primary_contact,
                "contact": {
                    "id": pc.contact.id,
                    "name": str(pc.contact),
                    "phone": pc.contact.cell_phone,
                    "email": pc.contact.email,
                },
            }
            for pc in pet.pet_contacts.all()
        ],
        "veterinary_center": (
            {
                "id": pet.veterinary_center.id,
                "name": pet.veterinary_center.name,
            }
            if pet.veterinary_center else None
        ),
        "status": pet.status,
        "inactive_at": (
            pet.inactive_at.isoformat()
            if pet.inactive_at else None
        ),
        "deceased_at": (
            pet.deceased_at.isoformat()
            if pet.deceased_at else None
        ),
        "archived_at": (
            pet.archived_at.isoformat()
            if pet.archived_at else None
        ),
        "clinical_record_status": pet.clinical_record_status,
    }