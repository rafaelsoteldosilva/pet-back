# api/interfaces/http/endpoints/center/create_center_staff_membership_endpoint.py

from __future__ import annotations

from typing import Any, cast

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.center.commands.create_center_staff_membership import (
    create_center_staff_membership,
)
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
)
from api.interfaces.http.presenters.center.center_staff_membership_presenter import (
    center_staff_membership_presenter,
)
from api.interfaces.http.serializers.center.create_center_staff_membership_serializer import (
    CreateCenterStaffMembershipSerializer,
)


class Create_center_staff_membership_endpoint(APIView):
    permission_classes = [IsAuthenticated]

    def post(
        self,
        request: Request,
        center_id: int,
    ) -> Response:
        actor_membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )

        if actor_membership.role != "CENTER_ADMIN":
            raise PermissionDenied(
                "Solo un administrador del centro puede crear membresías."
            )

        serializer = CreateCenterStaffMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(
            dict[str, Any],
            serializer.validated_data,
        )

        staff_membership = create_center_staff_membership(
            center_id=center_id,
            data=validated_data,
        )

        return Response(
            center_staff_membership_presenter(staff_membership),
            status=status.HTTP_201_CREATED,
        )