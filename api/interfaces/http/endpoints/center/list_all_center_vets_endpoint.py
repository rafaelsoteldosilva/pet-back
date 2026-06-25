# api/interfaces/http/endpoints/center/list_all_center_vets_endpoint.py

from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.center.queries.list_all_center_vets import list_all_center_vets
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
)
from api.interfaces.http.presenters.center.center_vet_presenter import (
    list_of_center_vets_presenter,
)


class List_all_center_vets_endpoint(APIView):
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

        center_vets = list_all_center_vets(
            center_id=center_id,
        )

        return Response(
            list_of_center_vets_presenter(center_vets),
            status=status.HTTP_200_OK,
        )