# api/interfaces/http/presenters/center/center_staff_membership_presenter.py

from __future__ import annotations

from typing import Any

from api.infrastructure.orm.models import Center_Staff_Membership


def center_staff_membership_presenter(
    membership: Center_Staff_Membership,
) -> dict[str, Any]:
    user = membership.user
    veterinary_center = membership.veterinary_center

    return {
        "id": membership.id,
        "role": membership.role,
        "work_email": membership.work_email,
        "work_phone": membership.work_phone,
        "job_title": membership.job_title,
        "professional_license_number": membership.professional_license_number,
        "is_active": membership.is_active,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "document_id": user.document_id,
            "country_code": user.country_code,
            "cell_phone": user.cell_phone,
            "is_active": user.is_active,
        },
        "veterinary_center": {
            "id": veterinary_center.id,
            "name": veterinary_center.name,
            "country_code": veterinary_center.country_code,
        },
    }
