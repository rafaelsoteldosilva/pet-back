# api/interfaces/urls.py

from django.urls import path

from api.interfaces.http.endpoints.catalog.get_species_and_breeds_allowed_for_center_endpoint import (
    GetAllowedSpeciesAndBreedsForCenterEndpoint,
)
from api.interfaces.http.endpoints.pet.get_all_pets_for_center_endpoint import (
    GetAllPetsForCenterEndpoint,
)
from api.interfaces.http.endpoints.pet.pet_basic_data_endpoint import GetOrUpdatePetBasicDataEndpoint

urlpatterns = [
    path(
        "pets/get-all-pets-for-center/<int:center_id>/",
        GetAllPetsForCenterEndpoint.as_view(),
        name="search_pets",
    ),
    path(
        "pets-get-or-update/<int:center_id>/<int:pet_id>/basic-data/",
        GetOrUpdatePetBasicDataEndpoint.as_view(),
        name="pet_basic_data",
    ),
    path(
        "catalog/species-breeds/<int:center_id>/",
        GetAllowedSpeciesAndBreedsForCenterEndpoint.as_view(),
        name="allowed_species_catalog",
    ),
]