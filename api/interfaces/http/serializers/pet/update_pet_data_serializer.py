# api/interfaces/http/serializers/pet/update_pet_data_serializer.py

from __future__ import annotations

from rest_framework import serializers

from api.shared.choices.choices import Choices_Sex, Choices_Size
from api.shared.utils.microchip_validator import microchip_validator


class UpdatePetDataSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        min_length=1,
        max_length=100,
        allow_blank=False,
        trim_whitespace=True,
    )

    species_id = serializers.IntegerField(
        required=False,
    )

    breed_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    last_attending_vet_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    sex = serializers.ChoiceField(
        required=False,
        choices=Choices_Sex.choices,
    )

    sterilized = serializers.BooleanField(
        required=False,
    )

    birth_date = serializers.DateField(
        required=False,
        allow_null=True,
    )

    size = serializers.ChoiceField(
        required=False,
        choices=Choices_Size.choices,
        allow_blank=True,
        allow_null=True,
    )

    last_weight = serializers.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        allow_null=True,
    )

    body_description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=300,
        trim_whitespace=True,
    )

    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=100,
    )

    has_pedigree = serializers.BooleanField(
        required=False,
    )

    pedigree_registry = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=50,
    )

    visual_tag = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=20,
    )

    visual_identification_or_tattoo_description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=100,
    )

    has_microchip = serializers.BooleanField(
        required=False,
    )

    microchip_code = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=30,
        validators=[microchip_validator],
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
        max_length=80,
    )

    clinical_observations = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=150,
    )

    internal_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=100,
    )

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=300,
    )


__all__ = [
    "UpdatePetDataSerializer",
]