# api/interfaces/http/endpoints/auth/logout_endpoint.py

from __future__ import annotations

from typing import Any, Mapping, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _get_authenticated_user_id(*, request: Request) -> str:
    user_id = getattr(request.user, "id", None)

    if user_id is None:
        return ""

    return str(user_id)


def _get_refresh_token_user_id(*, refresh_token: RefreshToken) -> str:
    user_id_claim_name = cast(str, api_settings.USER_ID_CLAIM)

    token_user_id = refresh_token.get(user_id_claim_name)

    if token_user_id is None:
        return ""

    return str(token_user_id)


class LogoutEndpoint(APIView):
    """
    Logs out the authenticated user by blacklisting the provided refresh token.

    Important:
    - The user must already be authenticated with a valid access token.
    - The frontend must send the refresh token.
    - The frontend must not send user_id.
    - The refresh token must belong to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        payload = cast(Mapping[str, Any], request.data)

        refresh_token_value = _clean_string(payload.get("refresh"))

        if not refresh_token_value:
            return Response(
                {
                    "detail": "El refresh token es obligatorio.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            refresh_token = RefreshToken(cast(Any, refresh_token_value))
        except TokenError:
            return Response(
                {
                    "detail": "El refresh token no es válido.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        authenticated_user_id = _get_authenticated_user_id(request=request)
        refresh_token_user_id = _get_refresh_token_user_id(
            refresh_token=refresh_token,
        )

        if not authenticated_user_id:
            return Response(
                {
                    "detail": "Usuario no autenticado.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if refresh_token_user_id != authenticated_user_id:
            return Response(
                {
                    "detail": (
                        "El refresh token no pertenece al usuario autenticado."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            blacklistable_token = cast(Any, refresh_token)
            blacklistable_token.blacklist()
        except TokenError:
            return Response(
                {
                    "detail": "El refresh token no pudo ser invalidado.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)