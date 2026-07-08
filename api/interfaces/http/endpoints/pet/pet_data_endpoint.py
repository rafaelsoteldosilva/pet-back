# api/interfaces/http/endpoints/pet/pet_data_endpoint.py

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.pet.commands.create_pet import create_pet
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
from api.interfaces.http.serializers.pet.create_pet_data_serializer import (
    CreatePetDataSerializer,
)
from api.interfaces.http.serializers.pet.update_pet_data_serializer import (
    UpdatePetDataSerializer,
)


class Pet_data_endpoint(APIView):
    """
    Gets, updates, or creates pet data for the authenticated user's active center.

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

        raw_reason = data.pop("reason", None)

        reason: str | None
        if isinstance(raw_reason, str):
            reason = raw_reason.strip() or None
        else:
            reason = None

        try:
            created_pet = create_pet(
                veterinary_center_id=center_id,
                name=cast(str, data["name"]),
                sex=cast(str, data["sex"]),
                species_id=cast(int, data["species_id"]),
                actor=actor,
                membership=membership,
                breed_id=cast(int | None, data.get("breed_id")),
                sterilized=cast(bool, data.get("sterilized", False)),
                birth_date=cast(date | None, data.get("birth_date")),
                body_description=cast(
                    str | None,
                    data.get("body_description"),
                ),
                size=cast(str | None, data.get("size")),
                last_weight=cast(
                    Decimal | None,
                    data.get("last_weight"),
                ),
                last_attending_vet_id=cast(
                    int | None,
                    data.get("last_attending_vet_id"),
                ),
                reference=cast(str | None, data.get("reference")),
                has_pedigree=cast(bool, data.get("has_pedigree", False)),
                pedigree_registry=cast(
                    str | None,
                    data.get("pedigree_registry"),
                ),
                visual_tag=cast(str | None, data.get("visual_tag")),
                visual_identification_or_tattoo_description=cast(
                    str | None,
                    data.get(
                        "visual_identification_or_tattoo_description"
                    ),
                ),
                has_microchip=cast(
                    bool,
                    data.get("has_microchip", False),
                ),
                microchip_code=cast(
                    str | None,
                    data.get("microchip_code"),
                ),
                microchip_date=cast(
                    date | None,
                    data.get("microchip_date"),
                ),
                microchip_body_region=cast(
                    str | None,
                    data.get("microchip_body_region"),
                ),
                clinical_observations=cast(
                    str | None,
                    data.get("clinical_observations"),
                ),
                internal_notes=cast(
                    str | None,
                    data.get("internal_notes"),
                ),
                photo_url=cast(str | None, data.get("photo_url")),
                reason=reason,
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


__all__ = [
    "Pet_data_endpoint",
]