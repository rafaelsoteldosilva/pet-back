# api/interfaces/http/serializers/general/create_pet_control_user_serializer.py

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class CreatePetControlUserSerializer(serializers.Serializer):
    email = serializers.EmailField()

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        min_length=8,
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        min_length=8,
    )

    first_name = serializers.CharField(max_length=255)
    last_name = serializers.CharField(max_length=255)

    document_id = serializers.CharField(max_length=20)
    country_code = serializers.CharField(max_length=10)

    cell_phone = serializers.CharField(max_length=20)

    complete_address = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(
        self,
        attrs: dict[str, Any],
    ) -> dict[str, Any]:
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {
                    "password_confirm": "Las contraseñas no coinciden.",
                }
            )

        attrs.pop("password_confirm")

        return attrs