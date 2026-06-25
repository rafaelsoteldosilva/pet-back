from __future__ import annotations

from typing import Optional

from api.infrastructure.orm.models.catalog import (
    Global_Breed,
    Species_In_Center,
)


def get_allowed_species_ids_for_center(veterinary_center_id: int) -> list[int]:
    """
    Returns the global species IDs enabled for a veterinary center.
    Only active center-species relations are included.
    """
    return list(
        Species_In_Center.objects.filter(
            veterinary_center_id=veterinary_center_id,
            is_active=True,
        ).values_list("global_species_id", flat=True)
    )


def get_species_id_for_breed(breed_id: int) -> Optional[int]:
    """
    Returns the global species ID that owns the given global breed ID.
    """
    return (
        Global_Breed.objects.filter(id=breed_id)
        .values_list("species_id", flat=True)
        .first()
    )