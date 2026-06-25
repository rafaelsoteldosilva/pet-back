# api/interfaces/http/endpoints/pet/pet_data_endpoint.py

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.commands.update_pet import update_pet
from api.application.pet.dto.pet_data_dto import Pet_Data_DTO
from api.application.pet.queries.get_pet_data import get_pet_data
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
)
from api.infrastructure.orm.models.user import Pet_Control_User
from api.interfaces.http.presenters.pet.pet_data_presenter import (
    pet_data_presenter,
)
from api.interfaces.http.responses.validation_error_response import (
    build_django_validation_error_response,
)
from api.interfaces.http.serializers.pet.update_pet_data_serializer import (
    UpdatePetBasicDataSerializer,
)


class Pet_data_endpoint(APIView):
    """
    Gets or updates pet data for the authenticated user's active center.

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
        pet_id: int,
    ) -> Response:
        _ = self

        get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )

        pet_data: Pet_Data_DTO = get_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        return Response(
            pet_data_presenter(pet_data),
            status=status.HTTP_200_OK,
        )

    def patch(
        self: Any,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:
        _ = self
        membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )
        actor = cast(Pet_Control_User, request.user)

        serializer = UpdatePetBasicDataSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        data = dict(validated_data)

        reason = cast(str | None, data.pop("reason", None))

        try:
            update_pet(
                center_id=center_id,
                pet_id=pet_id,
                data=data,
                actor=actor,
                membership=membership,
                reason=reason,
            )
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        updated_pet_data: Pet_Data_DTO = get_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        return Response(
            pet_data_presenter(updated_pet_data),
            status=status.HTTP_200_OK,
        )


__all__ = [
    "Pet_data_endpoint",
]