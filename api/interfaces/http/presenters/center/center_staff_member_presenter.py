# api/interfaces/http/presenters/center/center_staff_member_presenter.py

from __future__ import annotations

from typing import Any

from api.infrastructure.orm.models import Center_Staff_Member


def center_staff_member_presenter(
    member: Center_Staff_Member,
) -> dict[str, Any]:
    user = member.user
    veterinary_center = member.veterinary_center

    return {
        "id": member.id,
        "role": member.role,
        "work_email": member.work_email,
        "work_phone": member.work_phone,
        "job_title": member.job_title,
        "professional_license_number": member.professional_license_number,
        "is_active": member.is_active,
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
