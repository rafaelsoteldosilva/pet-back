# api/interfaces/http/serializers/pet/update_pet_contact_link_serializer.py

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Pet_Contact_Link_Role,
)
from api.shared.utils.normalize_document_id import (
    is_valid_chilean_rut,
    normalize_document_id,
)


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _raise_invalid_document_id() -> None:
    raise serializers.ValidationError(
        {
            "document_id": [
                "El documento indicado no es un RUT chileno válido.",
            ]
        }
    )


def _validate_document_id_for_serializer(document_id: str) -> None:
    """
    Empty document_id is allowed in this PATCH serializer.

    But when a document_id is provided, it must be a valid Chilean RUT/RUN.
    The actual verifier-digit formula lives in is_valid_chilean_rut().
    """

    if not document_id:
        return

    if not is_valid_chilean_rut(document_id):
        _raise_invalid_document_id()


def _normalize_document_id(value: Any) -> str:
    document_id = _clean_string(value)

    if not document_id:
        return ""

    normalized_document_id = normalize_document_id(document_id)

    if not normalized_document_id:
        _raise_invalid_document_id()

    _validate_document_id_for_serializer(normalized_document_id)

    return normalized_document_id


class UpdatePetContactLinkSerializer(serializers.Serializer):
    """
    PATCH serializer for updating an existing Pet_Contact_Link and its related
    Center_Contact record.

    It accepts partial payloads. For example:

    {
        "document_id": "12345678-9"
    }
    """

    center_contact_type = serializers.ChoiceField(
        choices=Choices_Center_Contact_Type.choices,
        required=False,
    )

    # Center_Contact identity fields.
    first_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        trim_whitespace=True,
    )
    last_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        trim_whitespace=True,
    )
    institution_name = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=150,
        trim_whitespace=True,
    )

    # Center_Contact identification.
    document_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=50,
        trim_whitespace=True,
    )

    # Center_Contact communication/address data.
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=254,
    )
    primary_phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=30,
        trim_whitespace=True,
    )
    secondary_phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=30,
        trim_whitespace=True,
    )
    tertiary_phone = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=30,
        trim_whitespace=True,
    )
    address = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=255,
        trim_whitespace=True,
    )
    city = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        trim_whitespace=True,
    )
    region = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        trim_whitespace=True,
    )
    country = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=100,
        trim_whitespace=True,
    )
    center_contact_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
        trim_whitespace=True,
    )

    # Pet_Contact_Link relationship data.
    role = serializers.ChoiceField(
        choices=Choices_Pet_Contact_Link_Role.choices,
        required=False,
    )
    specific_relationship = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=80,
        trim_whitespace=True,
    )

    # Pet_Contact_Link permissions / flags.
    is_primary_contact = serializers.BooleanField(required=False)
    is_emergency_contact = serializers.BooleanField(required=False)
    can_authorize_treatment = serializers.BooleanField(required=False)
    can_receive_medical_updates = serializers.BooleanField(required=False)
    can_receive_billing = serializers.BooleanField(required=False)
    can_pickup_pet = serializers.BooleanField(required=False)

    pet_contact_link_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=500,
        trim_whitespace=True,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        center_contact_type = attrs.get("center_contact_type")
        role = attrs.get("role")

        if (
            center_contact_type
            == Choices_Center_Contact_Type.PERSON.value
            and role
        ):
            if not Choices_Pet_Contact_Link_Role.is_person_role(str(role)):
                raise serializers.ValidationError(
                    {
                        "role": [
                            "Este rol no es válido para un contacto de tipo persona.",
                        ]
                    }
                )

        if (
            center_contact_type
            == Choices_Center_Contact_Type.INSTITUTION.value
            and role
        ):
            if not Choices_Pet_Contact_Link_Role.is_institution_role(
                str(role)
            ):
                raise serializers.ValidationError(
                    {
                        "role": [
                            "Este rol no es válido para un contacto de tipo institución.",
                        ]
                    }
                )

        string_fields = (
            "first_name",
            "last_name",
            "institution_name",
            "email",
            "primary_phone",
            "secondary_phone",
            "tertiary_phone",
            "address",
            "city",
            "region",
            "country",
            "center_contact_notes",
            "specific_relationship",
            "pet_contact_link_notes",
        )

        for field_name in string_fields:
            if field_name in attrs:
                attrs[field_name] = _clean_string(attrs[field_name])

        if "document_id" in attrs:
            attrs["document_id"] = _normalize_document_id(
                attrs["document_id"]
            )

        if (
            attrs.get("role")
            == Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value
        ):
            attrs["can_receive_billing"] = True

        return attrs


__all__ = [
    "UpdatePetContactLinkSerializer",
]