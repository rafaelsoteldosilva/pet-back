# api/interfaces/http/serializers/pet/update_pet_basic_data_serializer.py

from rest_framework import serializers


class UpdatePetBasicDataSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=False,
        min_length=2,
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )

    species_id = serializers.IntegerField(required=False)

    breed_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    sex = serializers.ChoiceField(
        required=False,
        choices=["m", "f", "u"],
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
    )

    size = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    last_weight = serializers.DecimalField(
        required=False,
        max_digits=8,
        decimal_places=2,
        allow_null=True,
    )