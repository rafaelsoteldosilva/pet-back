# api/interfaces/http/presenters/auth/available_login_centers_presenter.py

from __future__ import annotations

from typing import Any, Iterable

from api.infrastructure.orm.models import Center_Staff_Membership


def available_login_centers_presenter(
    memberships: Iterable[Center_Staff_Membership],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "centers": [
            {
                "id": membership.veterinary_center.id,
                "name": membership.veterinary_center.name,
                "role": membership.role,
            }
            for membership in memberships
        ]
    }
