# api/interfaces/http/serializers/center/create_center_staff_member_serializer.py

from __future__ import annotations

from rest_framework import serializers


CENTER_STAFF_ROLE_CHOICES = [
    "CENTER_ADMIN",
    "VETERINARIAN",
    "ASSISTANT",
    "RECEPTIONIST",
    "VIEWER",
]


class CreateCenterStaffMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    role = serializers.ChoiceField(
        choices=CENTER_STAFF_ROLE_CHOICES,
    )

    work_email = serializers.EmailField(
        required=False,
        allow_blank=True,
    )

    work_phone = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    job_title = serializers.CharField(
        max_length=255,
    )

    professional_license_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
