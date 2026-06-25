# api/interfaces/http/endpoints/center/center_contact_endpoint.py

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.application.center.commands.add_center_contact import (
    add_center_contact,
)
from api.application.center.commands.delete_center_contact import (
    delete_center_contact,
)
from api.application.center.commands.update_center_contact import (
    update_center_contact,
)
from api.application.center.errors import (
    CenterContactHasPetContactLinksError,
    CenterContactNotFoundError,
    VeterinaryCenterNotFoundError,
)
from api.application.shared.permissions.center_membership import (
    get_active_center_membership,
)
from api.infrastructure.orm.models.user import Pet_Control_User
from api.interfaces.http.presenters.center.center_contact_presenter import (
    present_center_contact,
)
from api.interfaces.http.responses.validation_error_response import (
    build_django_validation_error_response,
)
from api.interfaces.http.serializers.center.add_center_contact_serializer import (
    Add_center_contact_serializer,
)


def _format_pet_names_for_message(pet_names: list[str]) -> str:
    clean_pet_names = [name.strip() for name in pet_names if name.strip()]

    if not clean_pet_names:
        return "una o más mascotas"

    if len(clean_pet_names) == 1:
        return clean_pet_names[0]

    if len(clean_pet_names) == 2:
        return f"{clean_pet_names[0]} y {clean_pet_names[1]}"

    return f"{clean_pet_names[0]}, {clean_pet_names[1]} y {clean_pet_names[2]}"


def _build_contact_has_pet_links_message(
    error: CenterContactHasPetContactLinksError,
) -> str:
    pet_names_text = _format_pet_names_for_message(error.pet_names)
    remaining_pet_count = error.total_linked_pets - len(error.pet_names)

    extra_text = ""

    if remaining_pet_count == 1:
        extra_text = ". Además, tiene 1 mascota más vinculada"
    elif remaining_pet_count > 1:
        extra_text = f". Además, tiene {remaining_pet_count} mascotas más vinculadas"

    return (
        "No puedes eliminar este contacto porque está vinculado a "
        f"{pet_names_text}{extra_text}. Primero debes quitar esos vínculos "
        "desde la ficha de las mascotas correspondientes."
    )


class Center_contact_endpoint(APIView):
    """
    Creates, updates, and deletes center contacts.

    Security:
    - The user must be authenticated.
    - The URL center_id must match the active_center_id in the token.
    - The user must have an active membership in that center.
    """

    permission_classes = [IsAuthenticated]

    def post(
        self,
        request: Request,
        center_id: int,
    ) -> Response:
        membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )
        actor = cast(Pet_Control_User, request.user)

        serializer = Add_center_contact_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)

        try:
            center_contact = add_center_contact(
                center_id=center_id,
                data=validated_data,
                actor=actor,
                membership=membership,
                reason=cast(str | None, validated_data.get("reason")),
            )
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        return Response(
            present_center_contact(center_contact),
            status=status.HTTP_201_CREATED,
        )

    def delete(
        self,
        request: Request,
        center_id: int,
        center_contact_id: int,
    ) -> Response:
        membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )
        actor = cast(Pet_Control_User, request.user)

        try:
            delete_center_contact(
                center_id=center_id,
                center_contact_id=center_contact_id,
                actor=actor,
                membership=membership,
                reason=None,
            )
        except VeterinaryCenterNotFoundError as exc:
            raise NotFound("Centro veterinario no encontrado.") from exc
        except CenterContactNotFoundError as exc:
            raise NotFound("Contacto del centro no encontrado.") from exc
        except CenterContactHasPetContactLinksError as exc:
            return Response(
                {
                    "detail": _build_contact_has_pet_links_message(exc),
                    "pet_names": exc.pet_names,
                    "total_linked_pets": exc.total_linked_pets,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(
        self,
        request: Request,
        center_id: int,
        center_contact_id: int,
    ) -> Response:
        membership = get_active_center_membership(
            actor=request.user,
            center_id=center_id,
            token=request.auth,
        )
        actor = cast(Pet_Control_User, request.user)

        serializer = Add_center_contact_serializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        validated_data = cast(dict[str, Any], serializer.validated_data)

        try:
            center_contact = update_center_contact(
                center_id=center_id,
                center_contact_id=center_contact_id,
                data=validated_data,
                actor=actor,
                membership=membership,
                reason=cast(str | None, validated_data.get("reason")),
            )
        except VeterinaryCenterNotFoundError as exc:
            raise NotFound("Centro veterinario no encontrado.") from exc
        except CenterContactNotFoundError as exc:
            raise NotFound("Contacto del centro no encontrado.") from exc
        except DjangoValidationError as exc:
            return build_django_validation_error_response(exc)

        return Response(
            present_center_contact(center_contact),
            status=status.HTTP_200_OK,
        )


__all__ = [
    "Center_contact_endpoint",
]