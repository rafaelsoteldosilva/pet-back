# api/interfaces/http/presenters/auth/available_login_centers_presenter.py

from __future__ import annotations

from typing import Any, Iterable

from api.infrastructure.orm.models import Center_Staff_Membership
from api.shared.choices.choices import Choices_Role


def available_login_centers_presenter(
    memberships: Iterable[Center_Staff_Membership],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "centers": [
            {
                "id": membership.veterinary_center.id,
                "name": membership.veterinary_center.name,
                "role": membership.role,
                "role_label": Choices_Role(membership.role).label,
            }
            for membership in memberships
        ]
    }