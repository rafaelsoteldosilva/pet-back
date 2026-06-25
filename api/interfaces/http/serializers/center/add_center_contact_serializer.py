# api/interfaces/http/serializers/center/add_center_contact_serializer.py

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from api.shared.choices.choices import Choices_Center_Contact_Type
from api.shared.utils.normalize_document_id import (
    is_valid_chilean_rut,
    normalize_document_id,
)


class Add_center_contact_serializer(serializers.Serializer):
    center_contact_type = serializers.ChoiceField(
        choices=Choices_Center_Contact_Type.choices,
        required=True,
    )

    # center_Contact identity fields.
    first_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    last_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    institution_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    # Center_Contact identification.
    document_id = serializers.CharField(
        max_length=50,
        required=True,
        allow_blank=False,
        trim_whitespace=True,
    )

    # Center_Contact communication/address data.
    email = serializers.EmailField(
        max_length=254,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    primary_phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    secondary_phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    tertiary_phone = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    address = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    region = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        center_contact_type = str(
            attrs.get("center_contact_type", "")
        )

        document_id = self._normalize_and_validate_document_id(
            attrs.get("document_id")
        )
        attrs["document_id"] = document_id

        first_name = self._clean_nullable_text(attrs.get("first_name"))
        last_name = self._clean_nullable_text(attrs.get("last_name"))
        institution_name = self._clean_nullable_text(
            attrs.get("institution_name")
        )

        attrs["first_name"] = first_name
        attrs["last_name"] = last_name
        attrs["institution_name"] = institution_name

        attrs["email"] = self._clean_nullable_text(attrs.get("email"))
        attrs["primary_phone"] = self._clean_nullable_text(
            attrs.get("primary_phone")
        )
        attrs["secondary_phone"] = self._clean_nullable_text(
            attrs.get("secondary_phone")
        )
        attrs["tertiary_phone"] = self._clean_nullable_text(
            attrs.get("tertiary_phone")
        )
        attrs["address"] = self._clean_nullable_text(attrs.get("address"))
        attrs["city"] = self._clean_nullable_text(attrs.get("city"))
        attrs["region"] = self._clean_nullable_text(attrs.get("region"))
        attrs["country"] = self._clean_nullable_text(attrs.get("country"))
        attrs["notes"] = self._clean_nullable_text(attrs.get("notes"))

        if (
            center_contact_type
            == Choices_Center_Contact_Type.PERSON.value
        ):
            if not first_name and not last_name:
                raise serializers.ValidationError(
                    {
                        "first_name": (
                            "Ingresa al menos el nombre o el apellido de la persona."
                        ),
                        "last_name": (
                            "Ingresa al menos el nombre o el apellido de la persona."
                        ),
                    }
                )

            if institution_name:
                raise serializers.ValidationError(
                    {
                        "institution_name": (
                            "institution_name no debe enviarse para un contacto "
                            "de tipo persona."
                        )
                    }
                )

        elif (
            center_contact_type
            == Choices_Center_Contact_Type.INSTITUTION.value
        ):
            if not institution_name:
                raise serializers.ValidationError(
                    {
                        "institution_name": (
                            "El nombre de la institución es obligatorio."
                        ),
                    }
                )

            if first_name or last_name:
                raise serializers.ValidationError(
                    {
                        "first_name": (
                            "first_name no debe enviarse para un contacto "
                            "de tipo institución."
                        ),
                        "last_name": (
                            "last_name no debe enviarse para un contacto "
                            "de tipo institución."
                        ),
                    }
                )

        else:
            raise serializers.ValidationError(
                {
                    "center_contact_type": "Tipo de contacto inválido.",
                }
            )

        return attrs

    @staticmethod
    def _clean_nullable_text(value: Any) -> str:
        if value is None:
            return ""

        if not isinstance(value, str):
            return str(value).strip()

        return value.strip()

    @staticmethod
    def _normalize_and_validate_document_id(value: Any) -> str:
        if value is None:
            raise serializers.ValidationError(
                {
                    "document_id": [
                        "El documento es obligatorio.",
                    ]
                }
            )

        if not isinstance(value, str):
            document_id = str(value).strip()
        else:
            document_id = value.strip()

        if not document_id:
            raise serializers.ValidationError(
                {
                    "document_id": [
                        "El documento es obligatorio.",
                    ]
                }
            )

        normalized_document_id = normalize_document_id(document_id)

        if not normalized_document_id:
            raise serializers.ValidationError(
                {
                    "document_id": [
                        "El documento indicado no es válido.",
                    ]
                }
            )

        if not is_valid_chilean_rut(normalized_document_id):
            raise serializers.ValidationError(
                {
                    "document_id": [
                        "El documento indicado no es un RUT chileno válido.",
                    ]
                }
            )

        return normalized_document_id


__all__ = [
    "Add_center_contact_serializer",
]