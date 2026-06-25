# api/interfaces/http/serializers/auth/pet_control_token_obtain_pair_serializer.py

from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from api.infrastructure.orm.models.center import Center_Staff_Membership


class PetControlTokenObtainPairSerializer(TokenObtainPairSerializer):
    veterinary_center_id = serializers.IntegerField(write_only=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        veterinary_center_id = int(attrs.pop("veterinary_center_id"))

        response_data: dict[str, Any] = dict(super().validate(attrs))

        if self.user is None:
            raise serializers.ValidationError(
                {
                    "detail": "No fue posible autenticar al usuario.",
                }
            )

        user = cast(Any, self.user)

        try:
            membership = (
                Center_Staff_Membership.objects.select_related(
                    "veterinary_center",
                    "user",
                )
                .get(
                    user=user,
                    veterinary_center_id=veterinary_center_id,
                    veterinary_center__is_active=True,
                    is_active=True,
                )
            )
        except Center_Staff_Membership.DoesNotExist as exc:
            raise serializers.ValidationError(
                {
                    "veterinary_center_id": (
                        "El usuario no pertenece al centro veterinario indicado "
                        "o su membresía no está activa."
                    )
                }
            ) from exc

        refresh = cast(RefreshToken, self.get_token(user))

        active_center_id = cast(int, membership.veterinary_center_id)
        active_personnel_id = membership.id
        active_center_name = str(membership.veterinary_center.name)
        active_center_role = str(membership.role)

        refresh["active_center_id"] = active_center_id
        refresh["active_center_name"] = active_center_name
        refresh["active_center_role"] = active_center_role
        refresh["active_personnel_id"] = active_personnel_id

        response_data["refresh"] = str(refresh)
        response_data["access"] = str(refresh.access_token)

        response_data["user"] = {
            "id": int(user.id),
            "username": str(user.get_username()),
            "email": str(getattr(user, "email", "") or ""),
            "first_name": str(getattr(user, "first_name", "") or ""),
            "last_name": str(getattr(user, "last_name", "") or ""),
        }

        response_data["active_center"] = {
            "id": active_center_id,
            "name": active_center_name,
            "role": active_center_role,
            "personnel_id": active_personnel_id,
        }

        return response_data