# api/interfaces/http/serializers/auth/available_login_centers_serializer.py

from __future__ import annotations

from rest_framework import serializers


class AvailableLoginCentersSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    password = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=False,
        write_only=True,
        style={"input_type": "password"},
    )