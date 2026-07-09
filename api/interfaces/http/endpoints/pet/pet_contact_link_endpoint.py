# api/interfaces/http/endpoints/pet/pet_contact_link_endpoint.py

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.commands.add_pet_contact_link import (
    add_pet_contact_link_to_pet,
)
from api.application.pet.commands.delete_pet_contact_link import (
    delete_pet_contact_link_from_pet,
)
from api.application.pet.commands.update_pet_contact_link import (
    PetContactLinkNotFoundError,
    update_pet_contact_link,
)
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
from api.interfaces.http.serializers.pet.add_pet_contact_link_serializer import (
    AddPetContactLinkSerializer,
)
from api.interfaces.http.serializers.pet.update_pet_contact_link_serializer import (
    UpdatePetContactLinkSerializer,
)


def _extract_optional_reason_from_request(request: Request) -> str | None:
    request_data = request.data

    if not isinstance(request_data, Mapping):
        return None

    raw_reason = request_data.get("reason")

    if not isinstance(raw_reason, str):
        return None

    reason = raw_reason.strip()

    if not reason:
        return None

    return reason


class Pet_contact_link_to_pet_endpoint(APIView):
    """
    Creates, updates, and deletes contact links for a pet.

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
        pet_id: int,
    ) -> Response:
        member = authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.CREATE_PET_CONTACT_LINK,
        )
        actor = cast(Pet_Control_User, request.user)

        serializer = AddPetContactLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = dict(cast(dict[str, Any], serializer.validated_data))
        reason = cast(str | None, validated_data.pop("reason", None))

        try:
            add_pet_contact_link_to_pet(
                center_id=center_id,
                pet_id=pet_id,
                data=validated_data,
                actor=actor,
                member=member,
                reason=reason,
            )
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        updated_pet_data = get_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        return Response(
            pet_data_presenter(updated_pet_data),
            status=status.HTTP_201_CREATED,
        )

    def patch(
        self,
        request: Request,
        center_id: int,
        pet_id: int,
        pet_contact_link_id: int,
    ) -> Response:
        member = authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.UPDATE_PET_CONTACT_LINK,
        )
        actor = cast(Pet_Control_User, request.user)

        serializer = UpdatePetContactLinkSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = dict(cast(dict[str, Any], serializer.validated_data))
        reason = cast(str | None, validated_data.pop("reason", None))

        try:
            update_pet_contact_link(
                center_id=center_id,
                pet_id=pet_id,
                pet_contact_link_id=pet_contact_link_id,
                data=validated_data,
                actor=actor,
                member=member,
                reason=reason,
            )
        except PetContactLinkNotFoundError as exc:
            raise NotFound(str(exc)) from exc
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        updated_pet_data = get_pet_data(
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
        pet_contact_link_id: int,
    ) -> Response:
        member = authorize_center_action(
            request=request,
            center_id=center_id,
            permission=CenterPermission.DELETE_PET_CONTACT_LINK,
        )
        actor = cast(Pet_Control_User, request.user)
        reason = _extract_optional_reason_from_request(request)

        try:
            delete_pet_contact_link_from_pet(
                center_id=center_id,
                pet_id=pet_id,
                pet_contact_link_id=pet_contact_link_id,
                actor=actor,
                member=member,
                reason=reason,
            )
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        updated_pet_data = get_pet_data(
            center_id=center_id,
            pet_id=pet_id,
        )

        return Response(
            pet_data_presenter(updated_pet_data),
            status=status.HTTP_200_OK,
        )


__all__ = [
    "Pet_contact_link_to_pet_endpoint",
]