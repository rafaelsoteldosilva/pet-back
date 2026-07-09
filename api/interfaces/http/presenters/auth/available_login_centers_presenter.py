# api/interfaces/http/presenters/auth/available_login_centers_presenter.py

from __future__ import annotations

from typing import Any, Iterable

from api.infrastructure.orm.models import Center_Staff_Member
from api.shared.choices.choices import Choices_Role


def available_login_centers_presenter(
    members: Iterable[Center_Staff_Member],
) -> dict[str, list[dict[str, Any]]]:
    return {
        "centers": [
            {
                "id": member.veterinary_center.id,
                "name": member.veterinary_center.name,
                "role": member.role,
                "role_label": Choices_Role(member.role).label,
            }
            for member in members
        ]
    }