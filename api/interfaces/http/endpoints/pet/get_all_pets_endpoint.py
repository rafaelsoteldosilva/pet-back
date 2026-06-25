# api/interfaces/http/endpoints/pet/get_all_pets_endpoint.py

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.queries.get_all_pets_for_center import (
    get_all_pets_for_center,
)
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
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
    - The user must have an active membership in that center.
    """

    permission_classes = [IsAuthenticated]

    def get(
        self: Any,
        request: Request,
        center_id: int,
    ) -> Response:
        _ = self

        get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
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