# api/interfaces/http/endpoints/auth/me_endpoint.py

from __future__ import annotations

from typing import Any, cast

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.infrastructure.orm.models.center import Center_Staff_Member
from api.infrastructure.orm.models.user import Pet_Control_User


def _get_token_int_claim(
    *,
    token: Any | None,
    claim_name: str,
) -> int | None:
    if token is None:
        return None

    value = token.get(claim_name)

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class MeEndpoint(APIView):
    """
    Returns the authenticated global user, the active center session,
    and the list of active centers where the user has an active member.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = cast(Pet_Control_User, request.user)

        active_center_id = _get_token_int_claim(
            token=request.auth,
            claim_name="active_center_id",
        )

        active_member_id = _get_token_int_claim(
            token=request.auth,
            claim_name="active_member_id",
        )

        members = list(
            Center_Staff_Member.objects.select_related(
                "veterinary_center",
            )
            .filter(
                user=user,
                is_active=True,
                veterinary_center__is_active=True,
            )
            .order_by(
                "veterinary_center__name",
            )
        )

        centers = [
            {
                "member_id": member.id,
                "center_id": member.veterinary_center_id,
                "center_name": member.veterinary_center.name,
                "role": member.role,
                "job_title": member.job_title,
                "professional_license_number": member.professional_license_number,
                "work_email": member.work_email,
                "work_phone": member.work_phone,
            }
            for member in members
        ]

        active_member = None

        if active_member_id is not None:
            active_member = next(
                (
                    member
                    for member in members
                    if member.id == active_member_id
                ),
                None,
            )

        if active_member is None and active_center_id is not None:
            active_member = next(
                (
                    member
                    for member in members
                    if member.veterinary_center_id == active_center_id
                ),
                None,
            )

        active_center = None

        if active_member is not None:
            active_center = {
                "member_id": active_member.id,
                "id": active_member.veterinary_center_id,
                "name": active_member.veterinary_center.name,
                "role": active_member.role,
                "job_title": active_member.job_title,
                "professional_license_number": (
                    active_member.professional_license_number
                ),
                "work_email": active_member.work_email,
                "work_phone": active_member.work_phone,
            }

        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "full_name": user.full_name,
                    "document_id": user.document_id,
                    "country_code": user.country_code,
                    "cell_phone": user.cell_phone,
                    "is_2fa_enabled": user.is_2fa_enabled,
                },
                "active_center": active_center,
                "centers": centers,
            }
        )