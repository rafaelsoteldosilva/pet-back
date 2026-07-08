# api/interfaces/http/endpoints/pet/pet_data_endpoint.py

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.commands.delete_pet_draft import delete_pet_draft
from api.application.pet.commands.create_pet import create_pet
from api.application.pet.commands.update_pet import PetNotFoundError, update_pet
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

from api.interfaces.http.serializers.pet.create_pet_data_serializer import CreatePetDataSerializer
from api.interfaces.http.serializers.pet.update_pet_data_serializer import (
    UpdatePetDataSerializer,
)


class Pet_data_endpoint(APIView):
    """
    Gets, creates, or updates pet data for the authenticated user's active center.

    Security:
    - The user must be authenticated.
    - The URL center_id must match the active_center_id in the token.
    - The user must have an active membership in that center.
    """

    permission_classes = [IsAuthenticated]
    
    delete_mode: str | None = None

    def post(
        self: Any,
        request: Request,
        center_id: int,
    ) -> Response:
        _ = self

        membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )

        actor = cast(Pet_Control_User, request.user)

        serializer = CreatePetDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        data = dict(validated_data)

        contact_links = data.pop("contact_links", [])

        raw_reason = data.pop("reason", None)

        reason: str | None
        if isinstance(raw_reason, str):
            reason = raw_reason.strip() or None
        else:
            reason = None

        try:
            created_pet = create_pet(
                veterinary_center_id=center_id,
                actor=actor,
                membership=membership,
                contact_links=contact_links,
                reason=reason,
                **data,
            )
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        created_pet_data: Pet_Data_DTO = get_pet_data(
            center_id=center_id,
            pet_id=created_pet.id,
        )

        return Response(
            pet_data_presenter(created_pet_data),
            status=status.HTTP_201_CREATED,
        )

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

        current_pet_data: Pet_Data_DTO = get_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        serializer = UpdatePetDataSerializer(
            instance=current_pet_data,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        data = dict(validated_data)

        raw_reason = data.pop("reason", None)

        reason: str | None
        if isinstance(raw_reason, str):
            reason = raw_reason.strip() or None
        else:
            reason = None

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
        
    def delete(
        self: Any,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:
        membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )

        actor = cast(Pet_Control_User, request.user)

        raw_reason: Any = None

        if isinstance(request.data, dict):
            raw_reason = request.data.get("reason")

        reason: str | None
        if isinstance(raw_reason, str):
            reason = raw_reason.strip() or None
        else:
            reason = None

        try:
            if self.delete_mode == "draft":
                delete_pet_draft(
                    center_id=center_id,
                    pet_id=pet_id,
                    actor=actor,
                    membership=membership,
                    reason=reason,
                )

            elif self.delete_mode == "normal":
                return Response(
                    {
                        "detail": "Normal pet deletion is not implemented yet."
                    },
                    status=status.HTTP_501_NOT_IMPLEMENTED,
                )

            else:
                return Response(
                    {
                        "detail": "Delete mode is not configured for this endpoint."
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except PetNotFoundError:
            return Response(
                {
                    "detail": "Paciente no encontrado."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )


__all__ = [
    "Pet_data_endpoint",
]
