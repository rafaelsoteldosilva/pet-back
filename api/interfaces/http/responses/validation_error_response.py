# api/interfaces/http/responses/validation_error_response.py

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response


def _normalize_django_validation_error(
    exc: DjangoValidationError,
) -> dict[str, Any]:
    if hasattr(exc, "message_dict"):
        return {
            "errors": exc.message_dict,
        }

    if hasattr(exc, "messages"):
        return {
            "errors": exc.messages,
        }

    return {
        "errors": [str(exc)],
    }


def build_django_validation_error_response(
    exc: DjangoValidationError,
) -> Response:
    return Response(
        _normalize_django_validation_error(exc),
        status=status.HTTP_400_BAD_REQUEST,
    )


__all__ = [
    "build_django_validation_error_response",
]