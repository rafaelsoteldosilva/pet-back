# api/application/catalog/queries/get_allowed_species_and_breeds_for_center.py

from typing import TypedDict, cast

from django.db.models import Prefetch

from api.infrastructure.orm.models.catalog import (
    Breed_In_Center,
    Species_In_Center,
)


class BreedItemDict(TypedDict):
    id: int
    name: str


class SpeciesItemDict(TypedDict):
    id: int
    name: str


class AllowedSpeciesAndBreedsItemDict(TypedDict):
    species: SpeciesItemDict
    breeds: list[BreedItemDict]


def get_allowed_species_and_breeds_for_center(
    center_id: int,
) -> list[AllowedSpeciesAndBreedsItemDict]:
    species_in_center_qs = (
        Species_In_Center.objects.filter(
            veterinary_center_id=center_id,
            is_active=True,
        )
        .select_related("global_species")
        .prefetch_related(
            Prefetch(
                "species_in_center_breeds_in_center",
                queryset=Breed_In_Center.objects.filter(is_active=True)
                .select_related("global_breed")
                .order_by("global_breed__name"),
                to_attr="prefetched_breeds_in_center",
            )
        )
        .order_by("global_species__name")
    )

    result: list[AllowedSpeciesAndBreedsItemDict] = []

    for species_in_center in species_in_center_qs:
        prefetched_breeds = cast(
            list[Breed_In_Center],
            getattr(species_in_center, "prefetched_breeds_in_center", []),
        )

        breeds: list[BreedItemDict] = [
            {
                "id": breed_in_center.global_breed.id,
                "name": breed_in_center.global_breed.name,
            }
            for breed_in_center in prefetched_breeds
        ]

        result.append(
            {
                "species": {
                    "id": species_in_center.global_species.id,
                    "name": species_in_center.global_species.name,
                },
                "breeds": breeds,
            }
        )

    return result