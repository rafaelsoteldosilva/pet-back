# api/interfaces/http/serializers/pet/add_pet_contact_link_serializer.py

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from api.shared.choices.choices import Choices_Pet_Contact_Link_Role


class AddPetContactLinkSerializer(serializers.Serializer):
    center_contact_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    role = serializers.ChoiceField(
        choices=Choices_Pet_Contact_Link_Role.choices,
        required=True,
    )

    specific_relationship = serializers.CharField(
        max_length=80,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    is_primary_contact = serializers.BooleanField(
        required=False,
    )

    is_emergency_contact = serializers.BooleanField(
        required=False,
    )

    can_authorize_treatment = serializers.BooleanField(
        required=False,
    )

    can_receive_medical_updates = serializers.BooleanField(
        required=False,
    )

    can_receive_billing = serializers.BooleanField(
        required=False,
    )

    can_pickup_pet = serializers.BooleanField(
        required=False,
    )

    pet_contact_link_notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        role = str(attrs.get("role", ""))

        attrs["specific_relationship"] = self._clean_nullable_text(
            attrs.get("specific_relationship")
        )
        attrs["pet_contact_link_notes"] = self._clean_nullable_text(
            attrs.get("pet_contact_link_notes")
        )

        if role == Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value:
            attrs["can_receive_billing"] = True

        return attrs

    @staticmethod
    def _clean_nullable_text(value: Any) -> str:
        if value is None:
            return ""

        if not isinstance(value, str):
            return str(value).strip()

        return value.strip()


__all__ = [
    "AddPetContactLinkSerializer",
]