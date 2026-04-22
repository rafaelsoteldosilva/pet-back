# api/interfaces/http/endpoints/catalog/get_species_and_breeds_allowed_for_center.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request

from api.application.catalog.queries.get_allowed_species_and_breeds_for_center import (
    get_allowed_species_and_breeds_for_center,
)


class GetAllowedSpeciesAndBreedsForCenterEndpoint(APIView):

    def get(self, request: Request, center_id: int) -> Response:
        species_with_breeds = get_allowed_species_and_breeds_for_center(
            center_id=center_id,
        )

        return Response(species_with_breeds)