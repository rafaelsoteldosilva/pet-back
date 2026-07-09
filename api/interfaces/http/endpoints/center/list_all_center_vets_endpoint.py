# api/interfaces/http/endpoints/center/list_all_center_vets_endpoint.py

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.center.queries.list_all_center_vets import (
    list_all_center_vets,
)
from api.application.shared.permissions.center_authorization import (
    authorize_center_action,
)
from api.application.shared.permissions.center_permissions import (
    CenterPermission,
)
from api.interfaces.http.presenters.center.center_vet_presenter import (
    list_of_center_vets_presenter,
)


class List_all_center_vets_endpoint(APIView):
    """
    Returns active veterinarians for a center.

    Security:
    - The user must be authenticated.
    - The URL center_id must match the active_center_id in the token.
    - The user must have an active member in that center.
    - The user must have permission to view pet-related data.
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

        center_vets = list_all_center_vets(
            center_id=center_id,
        )

        return Response(
            list_of_center_vets_presenter(center_vets),
            status=status.HTTP_200_OK,
        )


__all__ = [
    "List_all_center_vets_endpoint",
]