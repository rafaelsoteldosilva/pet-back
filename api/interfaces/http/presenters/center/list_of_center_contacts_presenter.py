# api/interfaces/http/presenters/center/list_of_center_contacts_presenter.py

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from api.application.pet.dto.center_contact_dto import Center_Contact_DTO


def present_list_of_center_contacts(
    contacts: list[Center_Contact_DTO],
) -> list[dict[str, Any]]:
    return [
        asdict(contact)
        for contact in contacts
    ]


__all__ = [
    "present_list_of_center_contacts",
]