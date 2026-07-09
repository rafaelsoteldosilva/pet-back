# api/application/shared/permissions/center_permissions.py

from __future__ import annotations

from enum import Enum
from typing import Any

from rest_framework.exceptions import PermissionDenied


class CenterPermission(str, Enum):
    # Pets
    VIEW_PET = "view_pet"
    CREATE_PET = "create_pet"
    UPDATE_PET = "update_pet"
    DELETE_PET = "delete_pet"

    # Center contacts
    VIEW_CENTER_CONTACT = "view_center_contact"
    CREATE_CENTER_CONTACT = "create_center_contact"
    UPDATE_CENTER_CONTACT = "update_center_contact"
    DELETE_CENTER_CONTACT = "delete_center_contact"

    # Pet contact links
    CREATE_PET_CONTACT_LINK = "create_pet_contact_link"
    UPDATE_PET_CONTACT_LINK = "update_pet_contact_link"
    DELETE_PET_CONTACT_LINK = "delete_pet_contact_link"

    # Center administration
    MANAGE_STAFF = "manage_staff"
    MANAGE_CENTER_SETTINGS = "manage_center_settings"


ROLE_PERMISSIONS: dict[str, frozenset[CenterPermission]] = {
    "CENTER_ADMIN": frozenset(
        {
            # Pets
            CenterPermission.VIEW_PET,
            CenterPermission.CREATE_PET,
            CenterPermission.UPDATE_PET,
            CenterPermission.DELETE_PET,

            # Center contacts
            CenterPermission.VIEW_CENTER_CONTACT,
            CenterPermission.CREATE_CENTER_CONTACT,
            CenterPermission.UPDATE_CENTER_CONTACT,
            CenterPermission.DELETE_CENTER_CONTACT,

            # Pet contact links
            CenterPermission.CREATE_PET_CONTACT_LINK,
            CenterPermission.UPDATE_PET_CONTACT_LINK,
            CenterPermission.DELETE_PET_CONTACT_LINK,

            # Center administration
            CenterPermission.MANAGE_STAFF,
            CenterPermission.MANAGE_CENTER_SETTINGS,
        }
    ),
    "VETERINARIAN": frozenset(
        {
            # Pets
            CenterPermission.VIEW_PET,
            CenterPermission.CREATE_PET,
            CenterPermission.UPDATE_PET,
            CenterPermission.DELETE_PET,

            # Center contacts
            CenterPermission.VIEW_CENTER_CONTACT,
            CenterPermission.CREATE_CENTER_CONTACT,
            CenterPermission.UPDATE_CENTER_CONTACT,

            # Pet contact links
            CenterPermission.CREATE_PET_CONTACT_LINK,
            CenterPermission.UPDATE_PET_CONTACT_LINK,
            CenterPermission.DELETE_PET_CONTACT_LINK,
        }
    ),
    "ASSISTANT": frozenset(
        {
            # Pets
            CenterPermission.VIEW_PET,
            CenterPermission.CREATE_PET,
            CenterPermission.UPDATE_PET,

            # Center contacts
            CenterPermission.VIEW_CENTER_CONTACT,
            CenterPermission.CREATE_CENTER_CONTACT,
            CenterPermission.UPDATE_CENTER_CONTACT,

            # Pet contact links
            CenterPermission.CREATE_PET_CONTACT_LINK,
            CenterPermission.UPDATE_PET_CONTACT_LINK,
        }
    ),
    "RECEPTIONIST": frozenset(
        {
            # Pets
            CenterPermission.VIEW_PET,
            CenterPermission.CREATE_PET,
            CenterPermission.UPDATE_PET,

            # Center contacts
            CenterPermission.VIEW_CENTER_CONTACT,
            CenterPermission.CREATE_CENTER_CONTACT,
            CenterPermission.UPDATE_CENTER_CONTACT,

            # Pet contact links
            CenterPermission.CREATE_PET_CONTACT_LINK,
            CenterPermission.UPDATE_PET_CONTACT_LINK,
        }
    ),
    "VIEWER": frozenset(
        {
            # Pets
            CenterPermission.VIEW_PET,

            # Center contacts
            CenterPermission.VIEW_CENTER_CONTACT,
        }
    ),
}


def _normalize_role(role: Any) -> str:
    """
    Normalizes role values coming from models, enums, or plain strings.

    Expected final values:
    - CENTER_ADMIN
    - VETERINARIAN
    - ASSISTANT
    - RECEPTIONIST
    - VIEWER
    """

    raw_role = getattr(role, "value", role)
    normalized_role = str(raw_role).strip().upper()

    # Temporary compatibility for old database rows or old tokens.
    if normalized_role == "READ_ONLY":
        return "VIEWER"

    return normalized_role


def center_role_has_permission(
    *,
    role: Any | None = None,
    actor_role: Any | None = None,
    permission: CenterPermission,
) -> bool:
    """
    Returns True if the role has the required permission.

    Supports both parameter names:
    - role
    - actor_role

    This avoids breaking authorize_center_action(), which calls this logic
    using actor_role.
    """

    resolved_role = actor_role if actor_role is not None else role

    if resolved_role is None:
        return False

    normalized_role = _normalize_role(resolved_role)
    permissions = ROLE_PERMISSIONS.get(normalized_role, frozenset())

    return permission in permissions


def assert_center_permission(
    *,
    actor_role: Any | None = None,
    role: Any | None = None,
    permission: CenterPermission,
) -> None:
    """
    Raises PermissionDenied when the role does not have the required permission.

    Used by authorize_center_action().
    """

    if not center_role_has_permission(
        actor_role=actor_role,
        role=role,
        permission=permission,
    ):
        raise PermissionDenied(
            "No tienes permiso para realizar esta acción."
        )


def role_has_permission(
    *,
    role: Any,
    permission: CenterPermission,
) -> bool:
    return center_role_has_permission(
        role=role,
        permission=permission,
    )


def has_center_permission(
    *,
    role: Any,
    permission: CenterPermission,
) -> bool:
    return center_role_has_permission(
        role=role,
        permission=permission,
    )


__all__ = [
    "CenterPermission",
    "ROLE_PERMISSIONS",
    "assert_center_permission",
    "center_role_has_permission",
    "role_has_permission",
    "has_center_permission",
]