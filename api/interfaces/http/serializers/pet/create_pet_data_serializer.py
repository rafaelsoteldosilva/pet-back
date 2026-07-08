# api/interfaces/http/serializers/pet/create_pet_data_serializer.py

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class CreatePetDataSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=120,
    )

    sex = serializers.ChoiceField(
        required=True,
        choices=("m", "f", "u"),
    )

    species_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    breed_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )

    sterilized = serializers.BooleanField(required=False)

    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    body_description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    size = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    last_weight = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=8,
        decimal_places=2,
    )

    last_attending_vet_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
    )

    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    has_pedigree = serializers.BooleanField(required=False)

    pedigree_registry = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    visual_tag = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    visual_identification_or_tattoo_description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    has_microchip = serializers.BooleanField(required=False)

    microchip_code = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    microchip_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    microchip_body_region = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    clinical_observations = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    internal_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    photo_url = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        has_pedigree = attrs.get("has_pedigree", False)
        has_microchip = attrs.get("has_microchip", False)

        if not has_pedigree:
            attrs["pedigree_registry"] = None

        if not has_microchip:
            attrs["microchip_code"] = None
            attrs["microchip_date"] = None
            attrs["microchip_body_region"] = None

        return attrs


__all__ = [
    "CreatePetDataSerializer",
]