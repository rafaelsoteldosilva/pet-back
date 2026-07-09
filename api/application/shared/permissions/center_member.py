# api/application/shared/permissions/center_member.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied

from api.infrastructure.orm.models.center import Center_Staff_Member



def get_request_active_center_id(
    request: Any,
) -> int:
    """
    Extracts active_center_id from the authenticated JWT.

    Important:
    - The frontend must not send the actor role.
    - The token only identifies the active center.
    - The database remains the source of truth for the role.
    """

    auth = getattr(request, "auth", None)

    if auth is None:
        raise PermissionDenied("No se encontró un centro activo en la sesión.")

    raw_center_id: Any = None

    if hasattr(auth, "payload"):
        raw_center_id = auth.payload.get("active_center_id")
    elif isinstance(auth, dict):
        raw_center_id = auth.get("active_center_id")
    else:
        try:
            raw_center_id = auth.get("active_center_id")
        except AttributeError:
            raw_center_id = None

    if raw_center_id in (None, ""):
        raise PermissionDenied("No se encontró un centro activo en la sesión.")

    try:
        return int(raw_center_id)
    except (TypeError, ValueError) as exc:
        raise PermissionDenied("El centro activo de la sesión no es válido.") from exc


def get_active_center_member(
    *,
    actor: Any,
    center_id: int,
    token_center_id: int,
) -> Center_Staff_Member:
    """
    Returns the active staff member record for this user in this center.

    This verifies:
    - The request center matches the active center in the token.
    - The user has an active staff member record in that center.
    - The user account is active.

    This does not check permissions yet.
    Permission checking happens in center_permissions.py.
    """

    if token_center_id != center_id:
        raise PermissionDenied("El centro activo no coincide con el centro solicitado.")

    if actor is None or not getattr(actor, "is_authenticated", False):
        raise PermissionDenied("Debes iniciar sesión para realizar esta acción.")

    try:
        return (
            Center_Staff_Member.objects.select_related(
                "user",
                "veterinary_center",
            )
            .get(
                user=actor,
                veterinary_center_id=center_id,
                is_active=True,
                user__is_active=True,
            )
        )
    except Center_Staff_Member.DoesNotExist as exc:
        raise PermissionDenied("No tienes acceso activo a este centro.") from exc


__all__ = [
    "get_request_active_center_id",
    "get_active_center_member",
]
