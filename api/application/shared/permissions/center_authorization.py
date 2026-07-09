# api/application/shared/permissions/center_authorization.py

from __future__ import annotations

from typing import Any

from api.application.shared.permissions.center_member import (
    get_active_center_member,
    get_request_active_center_id,
)
from api.application.shared.permissions.center_permissions import (
    assert_center_permission,
)
from api.infrastructure.orm.models.center import Center_Staff_Member


def authorize_center_action(
    *,
    request: Any,
    center_id: int,
    permission: str,
) -> Center_Staff_Member:
    """
    Authorizes a user action inside a veterinary center.

    This function verifies:
    1. The token contains an active center.
    2. The active center matches the requested center.
    3. The authenticated user is an active staff member in that center.
    4. The staff member role has the required permission.

    Returns:
        CenterStaffMember:
            The authenticated actor's staff member record.
            Useful for audit logs because it contains the real role.
    """

    token_center_id = get_request_active_center_id(request)

    center_member = get_active_center_member(
        actor=request.user,
        center_id=center_id,
        token_center_id=token_center_id,
    )

    assert_center_permission(
        actor_role=center_member.role,
        permission=permission,
    )

    return center_member


__all__ = [
    "authorize_center_action",
]
