# api/interfaces/http/endpoints/center/get_all_center_contacts_endpoint.py

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.center.commands.get_all_center_contacts import (
    get_all_center_contacts,
)
from api.application.center.errors import VeterinaryCenterNotFoundError
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
)
from api.interfaces.http.presenters.center.list_of_center_contacts_presenter import present_list_of_center_contacts



class Get_all_center_contacts_endpoint(APIView):
    """
    Returns all contacts for the authenticated user's active center.

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

        try:
            contacts = get_all_center_contacts(
                center_id=center_id,
            )
        except VeterinaryCenterNotFoundError as exc:
            raise NotFound("Centro veterinario no encontrado.") from exc

        return Response(
            present_list_of_center_contacts(contacts),
            status=status.HTTP_200_OK,
        )


__all__ = [
    "Get_all_center_contacts_endpoint",
]