# api/interfaces/http/endpoints/catalog/get_species_and_breeds_allowed_for_center.py

from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.catalog.queries.get_allowed_species_and_breeds_for_center import (
    get_allowed_species_and_breeds_for_center,
)
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
)


class Get_allowed_species_and_breeds_for_center_endpoint(APIView):
    """
    Returns the species and breeds allowed for the authenticated user's
    active veterinary center.

    Security:
    - The user must be authenticated.
    - The requested center_id must match the active_center_id in the token.
    - The user must have an active membership in that center.
    """

    permission_classes = [IsAuthenticated]

    def get(
        self,
        request: Request,
        center_id: int,
    ) -> Response:
        get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )

        species_with_breeds = get_allowed_species_and_breeds_for_center(
            center_id=center_id,
        )

        return Response(species_with_breeds)