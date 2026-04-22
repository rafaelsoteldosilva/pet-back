
# api/application/catalog/queries/get_global_species_and_breeds.py

from django.db.models import Prefetch, QuerySet

from api.infrastructure.orm.models.catalog import (
    Global_Species,
    Global_Breed,
)


def get_global_species_and_breeds() -> list[dict[str, object]]:
    species_queryset: QuerySet[Global_Species] = (
        Global_Species.objects
        .prefetch_related(
            Prefetch(
                "breeds",
                queryset=Global_Breed.objects.order_by("name"),
            )
        )
        .order_by("name")
    )

    result: list[dict[str, object]] = []

    for species in species_queryset:
        breeds = [
            {
                "id": breed.id,
                "name": breed.name,
            }
            for breed in getattr(species, "breeds").all()
        ]

        result.append(
            {
                "id": species.pk,
                "name": species.name,
                "breeds": breeds,
            }
        )

    return result