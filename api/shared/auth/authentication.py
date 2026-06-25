# api/shared/auth/authentication.py

from __future__ import annotations

from typing import Any

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from api.infrastructure.orm.models.center import Center_Staff_Membership


class PersonnelJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token: Any) -> Any:
        user_id = validated_token.get("user_id")

        if user_id is None:
            raise AuthenticationFailed("Invalid token: user_id is missing.")

        try:
            user = Center_Staff_Membership.objects.get(pk=user_id)
        except Center_Staff_Membership.DoesNotExist as exc:
            raise AuthenticationFailed("Invalid user in JWT.") from exc

        if not user.is_active:
            raise AuthenticationFailed("User is inactive.")

        return user


__all__ = [
    "PersonnelJWTAuthentication",
]