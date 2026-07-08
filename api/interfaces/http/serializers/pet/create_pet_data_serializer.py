# api/interfaces/http/serializers/pet/create_pet_data_serializer.py

from __future__ import annotations

import re
from typing import Any

from rest_framework import serializers


PET_SEX_CHOICES = (
    ("m", "Macho"),
    ("f", "Hembra"),
    ("u", "Indefinido"),
)

PET_SIZE_CHOICES = (
    ("small", "Pequeño"),
    ("medium", "Mediano"),
    ("large", "Grande"),
    ("xlarge", "Gigante"),
)

PET_CONTACT_ROLE_CHOICES = (
    ("OWNER_GUARDIAN", "Propietario / Tutor"),
    ("CAREGIVER", "Cuidador"),
    ("BILLING_RESPONSIBLE", "Responsable de pago"),
    ("REFERRING_VET", "Veterinario remitente"),
    ("RESPONSIBLE_INSTITUTION", "Institución responsable"),
    ("REFERRING_INSTITUTION", "Institución remitente"),
    ("BREEDER", "Criador / Criadero"),
    ("SHELTER_OR_FOUNDATION", "Refugio / fundación"),
)


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    clean_value = str(value).strip()

    return clean_value or None


class CreatePetContactLinkSerializer(serializers.Serializer):
    center_contact_id = serializers.IntegerField(
        required=True,
        min_value=1,
    )

    role = serializers.ChoiceField(
        required=True,
        choices=PET_CONTACT_ROLE_CHOICES,
    )

    specific_relationship = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=100,
    )

    is_primary_contact = serializers.BooleanField(
        required=False,
        default=False,
    )

    is_emergency_contact = serializers.BooleanField(
        required=False,
        default=False,
    )

    can_authorize_treatment = serializers.BooleanField(
        required=False,
        default=False,
    )

    can_receive_medical_updates = serializers.BooleanField(
        required=False,
        default=False,
    )

    can_receive_billing = serializers.BooleanField(
        required=False,
        default=False,
    )

    can_pickup_pet = serializers.BooleanField(
        required=False,
        default=False,
    )

    pet_contact_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=300,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("role") == "BILLING_RESPONSIBLE":
            attrs["can_receive_billing"] = True

        attrs["specific_relationship"] = _clean_optional_text(
            attrs.get("specific_relationship"),
        )

        attrs["pet_contact_notes"] = _clean_optional_text(
            attrs.get("pet_contact_notes"),
        )

        return attrs


class CreatePetDataSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=120,
    )

    sex = serializers.ChoiceField(
        required=True,
        choices=PET_SEX_CHOICES,
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

    sterilized = serializers.BooleanField(
        required=False,
        default=False,
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
        max_length=300,
    )

    size = serializers.ChoiceField(
        required=False,
        allow_blank=True,
        allow_null=True,
        choices=PET_SIZE_CHOICES,
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
        max_length=100,
    )

    has_pedigree = serializers.BooleanField(
        required=False,
        default=False,
    )

    pedigree_registry = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=50,
    )

    has_visual_identification = serializers.BooleanField(
        required=False,
        default=False,
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
        default=False,
    )

    microchip_code = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
        max_length=30,
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
        max_length=500,
    )

    contact_links = CreatePetContactLinkSerializer(
        many=True,
        required=True,
        allow_empty=False,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        name = str(attrs.get("name", "")).strip()

        if not name:
            raise serializers.ValidationError({
                "name": "El nombre del paciente es obligatorio.",
            })

        attrs["name"] = name

        has_pedigree = bool(attrs.get("has_pedigree", False))
        pedigree_registry = _clean_optional_text(
            attrs.get("pedigree_registry"),
        )

        if has_pedigree and not pedigree_registry:
            raise serializers.ValidationError({
                "pedigree_registry": (
                    "El registro de pedigrí es obligatorio cuando "
                    "la mascota tiene pedigrí."
                ),
            })

        attrs["pedigree_registry"] = (
            pedigree_registry
            if has_pedigree
            else None
        )

        has_microchip = bool(attrs.get("has_microchip", False))
        microchip_code = _clean_optional_text(attrs.get("microchip_code"))

        if has_microchip:
            if not microchip_code:
                raise serializers.ValidationError({
                    "microchip_code": (
                        "El código del microchip es obligatorio cuando "
                        "la mascota tiene microchip."
                    ),
                })

            if not re.fullmatch(r"\d{15}", microchip_code):
                raise serializers.ValidationError({
                    "microchip_code": "El microchip debe tener 15 dígitos.",
                })

            attrs["microchip_code"] = microchip_code
            attrs["microchip_body_region"] = _clean_optional_text(
                attrs.get("microchip_body_region"),
            )
        else:
            attrs["microchip_code"] = None
            attrs["microchip_date"] = None
            attrs["microchip_body_region"] = None

        contact_links = attrs.get("contact_links") or []

        if not contact_links:
            raise serializers.ValidationError({
                "contact_links": "Debes agregar al menos un contacto principal.",
            })

        primary_contact_links = [
            link
            for link in contact_links
            if bool(link.get("is_primary_contact"))
        ]

        if len(primary_contact_links) == 0:
            raise serializers.ValidationError({
                "contact_links": "Debes marcar un contacto principal.",
            })

        if len(primary_contact_links) > 1:
            raise serializers.ValidationError({
                "contact_links": "Solo puede haber un contacto principal.",
            })

        contact_ids = [
            int(link["center_contact_id"])
            for link in contact_links
        ]

        if len(contact_ids) != len(set(contact_ids)):
            raise serializers.ValidationError({
                "contact_links": (
                    "No puedes agregar el mismo contacto más de una vez."
                ),
            })

        for optional_text_field in (
            "body_description",
            "reference",
            "visual_tag",
            "visual_identification_or_tattoo_description",
            "clinical_observations",
            "internal_notes",
            "photo_url",
            "reason",
        ):
            attrs[optional_text_field] = _clean_optional_text(
                attrs.get(optional_text_field),
            )

        attrs["has_visual_identification"] = bool(
            attrs.get("visual_tag")
            or attrs.get("visual_identification_or_tattoo_description")
        )

        return attrs


__all__ = [
    "CreatePetDataSerializer",
]