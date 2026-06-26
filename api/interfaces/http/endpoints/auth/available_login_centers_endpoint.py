# api/interfaces/http/endpoints/auth/available_login_centers_endpoint.py

from __future__ import annotations

from typing import TypedDict, cast

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.infrastructure.orm.models import Center_Staff_Membership
from api.interfaces.http.presenters.auth.available_login_centers_presenter import (
    available_login_centers_presenter,
)
from api.interfaces.http.serializers.auth.available_login_centers_serializer import (
    AvailableLoginCentersSerializer,
)


class AvailableLoginCentersValidatedData(TypedDict):
    email: str
    password: str


class Available_login_centers_endpoint(APIView):
    """
    Returns the active veterinary centers where the user has an active staff
    membership.

    This endpoint is intentionally public because it runs before JWT login.

    Security:
    - It does not return centers unless the email and password are valid.
    - It does not reveal whether the email exists.
    - It only returns active memberships in active centers.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = AvailableLoginCentersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(
            AvailableLoginCentersValidatedData,
            serializer.validated_data,
        )

        email = validated_data["email"]
        password = validated_data["password"]

        user_model = get_user_model()

        user = (
            user_model.objects.filter(
                email__iexact=email,
            )
            .first()
        )

        if user is None:
            return self._invalid_credentials_response()

        if not user.check_password(password):
            return self._invalid_credentials_response()

        if not user.is_active:
            return self._invalid_credentials_response()

        memberships = (
            Center_Staff_Membership.objects.select_related("veterinary_center")
            .filter(
                user=user,
                is_active=True,
                veterinary_center__is_active=True,
            )
            .order_by("veterinary_center__name")
        )

        response_data = available_login_centers_presenter(memberships)

        return Response(response_data, status=status.HTTP_200_OK)

    def _invalid_credentials_response(self) -> Response:
        return Response(
            {
                "detail": "Credenciales inválidas.",
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )