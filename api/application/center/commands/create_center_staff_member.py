# api/application/center/commands/create_center_staff_member.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from api.infrastructure.orm.models import (
    Center_Staff_Member,
    Veterinary_Center,
)
from api.infrastructure.orm.models.user import Pet_Control_User


def _raise_validation_error_from_django_error(
    exc: DjangoValidationError,
) -> None:
    if hasattr(exc, "message_dict"):
        raise ValidationError(exc.message_dict) from exc

    raise ValidationError({"detail": exc.messages}) from exc


@transaction.atomic
def create_center_staff_member(
    *,
    center_id: int,
    data: dict[str, Any],
) -> Center_Staff_Member:
    email = str(data["email"]).strip().lower()

    try:
        user = Pet_Control_User.objects.get(email=email)
    except Pet_Control_User.DoesNotExist as exc:
        raise ValidationError(
            {
                "email": "No existe un usuario con este correo electrónico.",
            }
        ) from exc

    if not user.is_active:
        raise ValidationError(
            {
                "email": (
                    "El usuario existe, pero todavía no está validado. "
                    "No puede ser vinculado a un centro todavía."
                ),
            }
        )

    try:
        veterinary_center = Veterinary_Center.objects.get(id=center_id)
    except Veterinary_Center.DoesNotExist as exc:
        raise ValidationError(
            {
                "center_id": "El centro veterinario indicado no existe.",
            }
        ) from exc

    if Center_Staff_Member.objects.filter(
        user=user,
        veterinary_center=veterinary_center,
    ).exists():
        raise ValidationError(
            {
                "detail": "Este usuario ya tiene una membresía en este centro.",
            }
        )

    staff_member = Center_Staff_Member(
        user=user,
        veterinary_center=veterinary_center,
        role=data["role"],
        work_email=data.get("work_email") or user.email,
        work_phone=data.get("work_phone") or user.cell_phone,
        job_title=data["job_title"],
        professional_license_number=data.get(
            "professional_license_number",
        )
        or None,
        is_active=True,
    )

    try:
        staff_member.full_clean()
        staff_member.save()

    except DjangoValidationError as exc:
        _raise_validation_error_from_django_error(exc)

    except IntegrityError as exc:
        raise ValidationError(
            {
                "detail": "No se pudo crear la membresía del usuario en el centro.",
            }
        ) from exc

    return staff_member
