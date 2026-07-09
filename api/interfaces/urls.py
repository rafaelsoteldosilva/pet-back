# api/interfaces/urls.py

from django.urls import include, path

from api.interfaces.http.endpoints.catalog.get_species_and_breeds_allowed_for_center_endpoint import (
    Get_allowed_species_and_breeds_for_center_endpoint,
)

from api.interfaces.http.endpoints.center.center_contact_endpoint import Center_contact_endpoint
from api.interfaces.http.endpoints.center.create_center_staff_membership_endpoint import Create_center_staff_membership_endpoint
from api.interfaces.http.endpoints.center.get_all_center_contacts_endpoint import Get_all_center_contacts_endpoint
from api.interfaces.http.endpoints.center.list_all_center_vets_endpoint import List_all_center_vets_endpoint
from api.interfaces.http.endpoints.general.create_pet_control_user_endpoint import Create_pet_control_user_endpoint
from api.interfaces.http.endpoints.pet.pet_data_endpoint import Pet_data_endpoint
from api.interfaces.http.endpoints.pet.pet_contact_link_endpoint import Pet_contact_link_to_pet_endpoint
from api.interfaces.http.endpoints.pet.get_all_pets_endpoint import Get_all_pets_endpoint


urlpatterns = [
    path(
        "users/",
        Create_pet_control_user_endpoint.as_view(),
        name="create-pet-control-user",
    ),
    path(
        "centers/<int:center_id>/staff-memberships/",
        Create_center_staff_membership_endpoint.as_view(),
        name="create-center-staff-membership",
    ),
    path("auth/", include("api.interfaces.http.urls.auth_urls")),
    path(
        "all-pets/<int:center_id>/",
        Get_all_pets_endpoint.as_view(),
        name="search_pets",
    ),
    path(
        "center-vets/<int:center_id>/",
        List_all_center_vets_endpoint.as_view(),
        name="list-all-center-vets",
    ),
    path(
        "all-center-contacts/<int:center_id>/",
        Get_all_center_contacts_endpoint.as_view(),
        name="get-center-contact",
    ),
    path(
        "center-contact/<int:center_id>/add/",
        Center_contact_endpoint.as_view(),
        name="add-center-contact",
    ),
    path(
        "center-contact/<int:center_id>/<int:center_contact_id>/delete/",
        Center_contact_endpoint.as_view(),
        name="delete-center-contact",
    ),
    path(
        "center-contact/<int:center_id>/<int:center_contact_id>/update/",
        Center_contact_endpoint.as_view(),
        name="update-center-contact",
    ),
    path(
        "pet/<int:center_id>/<int:pet_id>/get/",
        Pet_data_endpoint.as_view(),
        name="get-pet-data",
    ),
    path(
        "pet/<int:center_id>/<int:pet_id>/update/",
        Pet_data_endpoint.as_view(),
        name="update-pet-data",
    ),
    path(
        "pet/<int:center_id>/<int:pet_id>/delete/",
        Pet_data_endpoint.as_view(),
        name="delete-pet-data",
    ),
    path(
        "pet/<int:center_id>/create/",
        Pet_data_endpoint.as_view(),
        name="create-pet-data",
    ),
    path(
        "pet-contact-link/<int:center_id>/<int:pet_id>/add/",
        Pet_contact_link_to_pet_endpoint.as_view(),
        name="add-pet-contact",
    ),
    path(
        "pet-contact-link/<int:center_id>/<int:pet_id>/<int:pet_contact_link_id>/update/",
        Pet_contact_link_to_pet_endpoint.as_view(),
        name="update-pet-contact",
    ),
    path(
        "pet-contact-link/<int:center_id>/<int:pet_id>/<int:pet_contact_link_id>/delete/",
        Pet_contact_link_to_pet_endpoint.as_view(),
        name="delete-pet-contact",
    ),
    path(
        "all-catalog/species-breeds/<int:center_id>/",
        Get_allowed_species_and_breeds_for_center_endpoint.as_view(),
        name="allowed_species_catalog",
    ),
]