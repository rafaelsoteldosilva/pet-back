# api/interfaces/http/endpoints/pet/get_all_pets_endpoint.py

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.queries.get_all_pets_for_center import (
    get_all_pets_for_center,
)
from api.application.shared.permissions.center_authorization import (
    authorize_center_action,
)
from api.application.shared.permissions.center_permissions import (
    CenterPermission,
)
from api.interfaces.http.presenters.pet.all_pets_for_center_presenter import (
    present_search_pets_list,
)


class Get_all_pets_endpoint(APIView):
    """
    Returns pets for the authenticated user's active center.

    Security:
    - The user must be authenticated.
    - The URL center_id must match the active_center_id in the token.
    - The user must have an active member in that center.
    - The user must have permission to view pets.
    """

    permission_classes = [IsAuthenticated]

    def get(
        self,
        request: Request,
        center_id: int,
    ) -> Response:
        authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.VIEW_PET,
        )

        search_type = request.query_params.get("search_type")
        query = request.query_params.get("query")

        results = get_all_pets_for_center(
            veterinary_center_id=center_id,
            get_all_pets_for_center_type=search_type,
            query=query,
        )

        return Response(
            present_search_pets_list(results),
            status=status.HTTP_200_OK,
        )


__all__ = [
    "Get_all_pets_endpoint",
]