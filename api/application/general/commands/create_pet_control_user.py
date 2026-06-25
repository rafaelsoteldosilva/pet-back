# api/application/general/commands/create_pet_control_user.py

from __future__ import annotations

from typing import Any, NoReturn, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from api.infrastructure.orm.models.user import (
    Pet_Control_User,
    Pet_Control_User_Manager,
)


def _raise_validation_error_from_django_error(
    exc: DjangoValidationError,
) -> NoReturn:
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict) from exc

    raise ValidationError({"detail": exc.messages}) from exc


@transaction.atomic
def create_pet_control_user(
    *,
    data: dict[str, Any],
) -> Pet_Control_User:
    email = str(data["email"]).strip().lower()

    if Pet_Control_User.objects.filter(email=email).exists():
        raise ValidationError(
            {
                "email": "Ya existe un usuario con este correo electrónico.",
            }
        )

    user_manager = cast(
        Pet_Control_User_Manager,
        Pet_Control_User.objects,
    )

    try:
        return user_manager.create_user(
            email=email,
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            document_id=data["document_id"],
            country_code=data["country_code"],
            cell_phone=data["cell_phone"],
            complete_address=data.get("complete_address") or None,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )

    except DjangoValidationError as exc:
        _raise_validation_error_from_django_error(exc)

    except IntegrityError as exc:
        raise ValidationError(
            {
                "detail": (
                    "No se pudo crear el usuario. Revisa que el correo "
                    "o documento no estén duplicados."
                ),
            }
        ) from exc