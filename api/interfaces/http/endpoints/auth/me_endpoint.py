# api/interfaces/http/endpoints/auth/me_endpoint.py

from __future__ import annotations

from typing import Any, cast

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.infrastructure.orm.models.center import Center_Staff_Membership
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
    and the list of active centers where the user has an active membership.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = cast(Pet_Control_User, request.user)

        active_center_id = _get_token_int_claim(
            token=request.auth,
            claim_name="active_center_id",
        )

        active_membership_id = _get_token_int_claim(
            token=request.auth,
            claim_name="active_membership_id",
        )

        memberships = list(
            Center_Staff_Membership.objects.select_related(
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
                "membership_id": membership.id,
                "center_id": membership.veterinary_center_id,
                "center_name": membership.veterinary_center.name,
                "role": membership.role,
                "job_title": membership.job_title,
                "professional_license_number": membership.professional_license_number,
                "work_email": membership.work_email,
                "work_phone": membership.work_phone,
            }
            for membership in memberships
        ]

        active_membership = None

        if active_membership_id is not None:
            active_membership = next(
                (
                    membership
                    for membership in memberships
                    if membership.id == active_membership_id
                ),
                None,
            )

        if active_membership is None and active_center_id is not None:
            active_membership = next(
                (
                    membership
                    for membership in memberships
                    if membership.veterinary_center_id == active_center_id
                ),
                None,
            )

        active_center = None

        if active_membership is not None:
            active_center = {
                "membership_id": active_membership.id,
                "id": active_membership.veterinary_center_id,
                "name": active_membership.veterinary_center.name,
                "role": active_membership.role,
                "job_title": active_membership.job_title,
                "professional_license_number": (
                    active_membership.professional_license_number
                ),
                "work_email": active_membership.work_email,
                "work_phone": active_membership.work_phone,
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