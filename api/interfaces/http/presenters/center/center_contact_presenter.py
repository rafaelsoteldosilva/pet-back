# api/interfaces/http/presenters/center/center_contact_presenter.py

from __future__ import annotations

from typing import Any

from api.infrastructure.orm.models.center import Center_Contact


def present_center_contact(center_contact: Center_Contact) -> dict[str, Any]:
    return {
        "id": center_contact.id,
        "contact_type": center_contact.center_contact_type,
        "display_name": center_contact.display_name,
        "first_name": center_contact.first_name,
        "last_name": center_contact.last_name,
        "institution_name": center_contact.institution_name,
        "document_id": center_contact.document_id,
        "email": center_contact.email,
        "primary_phone": center_contact.primary_phone,
        "secondary_phone": center_contact.secondary_phone,
        "tertiary_phone": center_contact.tertiary_phone,
        "address": center_contact.address,
        "city": center_contact.city,
        "region": center_contact.region,
        "country": center_contact.country,
        "notes": center_contact.notes,
        "is_active": center_contact.is_active,
    }


__all__ = [
    "present_center_contact",
]