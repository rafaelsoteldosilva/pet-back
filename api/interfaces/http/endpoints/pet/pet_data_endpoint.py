# api/interfaces/http/endpoints/pet/pet_data_endpoint.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.commands.create_pet import create_pet
from api.application.pet.commands.delete_pet import (
    PetNotFoundError,
    delete_pet,
)
from api.application.pet.commands.update_pet import update_pet
from api.application.pet.dto.pet_data_dto import Pet_Data_DTO
from api.application.pet.queries.get_pet_data import get_pet_data
from api.application.shared.permissions.center_authorization import (
    authorize_center_action,
)
from api.application.shared.permissions.center_permissions import (
    CenterPermission,
)
from api.infrastructure.orm.models.user import Pet_Control_User
from api.interfaces.http.presenters.pet.pet_data_presenter import (
    pet_data_presenter,
)
from api.interfaces.http.responses.validation_error_response import (
    build_django_validation_error_response,
)
from api.interfaces.http.serializers.pet.create_pet_data_serializer import (
    CreatePetDataSerializer,
)
from api.interfaces.http.serializers.pet.update_pet_data_serializer import (
    UpdatePetDataSerializer,
)


def _normalize_optional_reason(raw_reason: Any) -> str | None:
    if not isinstance(raw_reason, str):
        return None

    reason = raw_reason.strip()

    if not reason:
        return None

    return reason


def _extract_optional_reason_from_request(request: Request) -> str | None:
    request_data = request.data

    if not isinstance(request_data, Mapping):
        return None

    return _normalize_optional_reason(request_data.get("reason"))


class Pet_data_endpoint(APIView):
    """
    Gets, creates, updates, or deletes pet data for the authenticated user's
    active center.

    Security:
    - The user must be authenticated.
    - The URL center_id must match the active_center_id in the token.
    - The user must have an active member in that center.
    - The user must have the required permission for the action.
    """

    permission_classes = [IsAuthenticated]

    def post(
        self,
        request: Request,
        center_id: int,
    ) -> Response:
        member = authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.CREATE_PET,
        )
        actor = cast(Pet_Control_User, request.user)

        serializer = CreatePetDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)
        data = dict(validated_data)

        contact_links = data.pop("contact_links", [])
        reason = _normalize_optional_reason(data.pop("reason", None))

        try:
            created_pet = create_pet(
                veterinary_center_id=center_id,
                actor=actor,
                member=member,
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
        self,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:
        authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.VIEW_PET,
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
        self,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:
        member = authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.UPDATE_PET,
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

        reason = _normalize_optional_reason(data.pop("reason", None))

        try:
            update_pet(
                center_id=center_id,
                pet_id=pet_id,
                data=data,
                actor=actor,
                member=member,
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
        self,
        request: Request,
        center_id: int,
        pet_id: int,
    ) -> Response:
        member = authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.DELETE_PET,
        )
        actor = cast(Pet_Control_User, request.user)

        reason = _extract_optional_reason_from_request(request)

        try:
            delete_pet(
                center_id=center_id,
                pet_id=pet_id,
                actor=actor,
                member=member,
                reason=reason,
            )
        except PetNotFoundError:
            return Response(
                {
                    "detail": "Paciente no encontrado.",
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