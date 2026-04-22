# api/interfaces/http/endpoints/pet/get_all_pets_for_center_endpoint.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request

from api.application.pet.queries.get_all_pets_for_center import get_all_pets_for_center
from api.interfaces.http.presenters.pet.get_all_pets_for_center_presenter import (
    present_search_pets_list,
)


class GetAllPetsForCenterEndpoint(APIView):

    def get(self, request: Request, center_id: int) -> Response:
        search_type = request.query_params.get("search_type")
        query = request.query_params.get("query")

        results = get_all_pets_for_center(
            veterinary_center_id=center_id,
            get_all_pets_for_center_type=search_type,
            query=query,
        )

        return Response(
            present_search_pets_list(results)
        )