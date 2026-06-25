# api/interfaces/http/presenters/general/pet_control_user_presenter.py

from __future__ import annotations

from typing import Any

from api.infrastructure.orm.models.user import Pet_Control_User


def pet_control_user_presenter(
    user: Pet_Control_User,
) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "document_id": user.document_id,
        "country_code": user.country_code,
        "cell_phone": user.cell_phone,
        "complete_address": user.complete_address,
        "is_active": user.is_active,
        "is_2fa_enabled": user.is_2fa_enabled,
    }
