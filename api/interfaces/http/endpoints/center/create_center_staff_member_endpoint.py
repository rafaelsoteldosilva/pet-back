# api/interfaces/http/endpoints/center/create_center_staff_member_endpoint.py

from __future__ import annotations

from typing import Any, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.center.commands.create_center_staff_member import (
    create_center_staff_member,
)
from api.application.shared.permissions.center_authorization import (
    authorize_center_action,
)
from api.application.shared.permissions.center_permissions import (
    CenterPermission,
)
from api.interfaces.http.presenters.center.center_staff_member_presenter import (
    center_staff_member_presenter,
)
from api.interfaces.http.serializers.center.create_center_staff_member_serializer import (
    CreateCenterStaffMemberSerializer,
)


class Create_center_staff_member_endpoint(APIView):
    """
    Creates a staff member for a center.

    Security:
    - The user must be authenticated.
    - The URL center_id must match the active_center_id in the token.
    - The user must have an active member in that center.
    - The user must have permission to manage staff.
    """

    permission_classes = [IsAuthenticated]

    def post(
        self,
        request: Request,
        center_id: int,
    ) -> Response:
        authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.MANAGE_STAFF,
        )

        serializer = CreateCenterStaffMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(
            dict[str, Any],
            serializer.validated_data,
        )

        staff_member = create_center_staff_member(
            center_id=center_id,
            data=validated_data,
        )

        return Response(
            center_staff_member_presenter(staff_member),
            status=status.HTTP_201_CREATED,
        )


__all__ = [
    "Create_center_staff_member_endpoint",
]