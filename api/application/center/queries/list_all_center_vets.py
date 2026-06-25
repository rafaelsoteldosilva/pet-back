# api/application/center/queries/list_all_center_vets.py

from __future__ import annotations

from api.infrastructure.orm.models.center import Center_Staff_Membership

VETERINARIAN_ROLE = "VETERINARIAN"


def list_all_center_vets(
    *,
    center_id: int,
) -> list[Center_Staff_Membership]:
    return list(
        Center_Staff_Membership.objects.select_related(
            "user",
            "veterinary_center",
        )
        .filter(
            veterinary_center_id=center_id,
            role=VETERINARIAN_ROLE,
            is_active=True,
            user__is_active=True,
        )
        .order_by(
            "user__last_name",
            "user__first_name",
            "id",
        )
    )