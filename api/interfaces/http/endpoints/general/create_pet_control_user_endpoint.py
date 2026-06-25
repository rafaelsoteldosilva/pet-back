# api/interfaces/http/endpoints/general/create_pet_control_user_endpoint.py

from __future__ import annotations

from typing import Any, cast

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.general.commands.create_pet_control_user import (
    create_pet_control_user,
)
from api.interfaces.http.presenters.general.pet_control_user_presenter import (
    pet_control_user_presenter,
)
from api.interfaces.http.serializers.general.create_pet_control_user_serializer import (
    CreatePetControlUserSerializer,
)


class Create_pet_control_user_endpoint(APIView):
    permission_classes = [AllowAny]

    def post(
        self,
        request: Request,
    ) -> Response:
        serializer = CreatePetControlUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(
            dict[str, Any],
            serializer.validated_data,
        )

        user = create_pet_control_user(
            data=validated_data,
        )

        return Response(
            pet_control_user_presenter(user),
            status=status.HTTP_201_CREATED,
        )