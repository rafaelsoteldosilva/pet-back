# api/application/shared/permissions/center_membership.py

from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import PermissionDenied

from api.infrastructure.orm.models.center import Center_Staff_Membership


Actor = AbstractBaseUser | AnonymousUser | None


def get_token_active_center_id(*, token: Any) -> int | None:
    if token is None:
        return None

    active_center_id = token.get("active_center_id")

    if active_center_id is None:
        return None

    try:
        return int(active_center_id)
    except (TypeError, ValueError):
        return None


def get_active_center_membership(
    *,
    actor: Actor,
    center_id: int,
    token: Any | None = None,
) -> Center_Staff_Membership:
    if actor is None:
        raise PermissionDenied("Usuario no autenticado.")

    if isinstance(actor, AnonymousUser) or not bool(actor.is_authenticated):
        raise PermissionDenied("Usuario no autenticado.")

    normalized_center_id = int(center_id)

    token_active_center_id = get_token_active_center_id(token=token)

    if (
        token_active_center_id is not None
        and token_active_center_id != normalized_center_id
    ):
        raise PermissionDenied(
            "El centro veterinario de la URL no coincide con el centro activo "
            "de la sesión."
        )

    django_user = actor

    try:
        return Center_Staff_Membership.objects.select_related(
            "user",
            "veterinary_center",
        ).get(
            user=django_user,
            veterinary_center_id=normalized_center_id,
            veterinary_center__is_active=True,
            is_active=True,
        )
    except Center_Staff_Membership.DoesNotExist as exc:
        raise PermissionDenied(
            "El usuario no pertenece al centro veterinario indicado."
        ) from exc