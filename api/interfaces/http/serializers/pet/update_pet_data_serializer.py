# api/interfaces/http/serializers/pet/update_pet_data_serializer.py

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class UpdatePetDataSerializer(serializers.Serializer):
    """
    Serializer used by PATCH /pet/pet-data/.

    Important:
    - This serializer validates the HTTP payload only.
    - Domain validation belongs in update_pet.py and the Pet model.
    - reason is accepted here so the endpoint can remove it before calling
      the command and pass it separately for audit logging.
    """

    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        write_only=True,
    )

    # Identity / core data
    name = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=True,
    )

    sex = serializers.CharField(
        required=False,
        allow_blank=False,
        trim_whitespace=True,
    )

    sterilized = serializers.BooleanField(
        required=False,
    )

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
        max_digits=10,
        decimal_places=3,
    )

    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    # Species / breed
    species_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    breed_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    # Last attending veterinarian
    #
    # Canonical field expected by update_pet.py:
    # - last_attending_vet_id
    #
    # Compatibility alias:
    # - last_attending_vet
    #
    # The model behind this FK is Center_Staff_Membership.
    last_attending_vet_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )

    last_attending_vet = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True,
    )

    last_attending_vet_external_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=150,
    )

    # Pedigree
    has_pedigree = serializers.BooleanField(
        required=False,
    )

    pedigree_registry = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )

    # Visual identification
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

    # Microchip
    has_microchip = serializers.BooleanField(
        required=False,
    )

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

    # Notes
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

    # Optional photo URL
    photo_url = serializers.URLField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """
        Normalizes legacy/alias fields and enforces simple payload consistency.

        Do not put database queries here.
        Keep cross-center and FK validation inside update_pet.py.
        """

        # Backward compatibility:
        # Some frontend code may still send last_attending_vet instead of
        # last_attending_vet_id.
        if (
            "last_attending_vet" in attrs
            and "last_attending_vet_id" not in attrs
        ):
            attrs["last_attending_vet_id"] = attrs["last_attending_vet"]

        attrs.pop("last_attending_vet", None)

        # Normalize blank optional text values to None where the domain treats
        # them as empty nullable data.
        nullable_text_fields = [
            "body_description",
            "size",
            "reference",
            "last_attending_vet_external_name",
            "pedigree_registry",
            "visual_tag",
            "visual_identification_or_tattoo_description",
            "microchip_code",
            "microchip_body_region",
            "clinical_observations",
            "internal_notes",
            "photo_url",
        ]

        for field_name in nullable_text_fields:
            value = attrs.get(field_name)

            if isinstance(value, str):
                cleaned_value = value.strip()
                attrs[field_name] = cleaned_value or None

        # Backend safety:
        # If pedigree is explicitly disabled, dependent data must not remain.
        if attrs.get("has_pedigree") is False:
            attrs["pedigree_registry"] = None

        # Backend safety:
        # If microchip is explicitly disabled, dependent data must not remain.
        if attrs.get("has_microchip") is False:
            attrs["microchip_code"] = None
            attrs["microchip_date"] = None
            attrs["microchip_body_region"] = None

        # Backend safety:
        # If an external veterinarian name is provided, the internal selected
        # veterinarian is intentionally irrelevant.
        external_vet_name = attrs.get("last_attending_vet_external_name")

        if external_vet_name:
            attrs["last_attending_vet_id"] = None

        return attrs