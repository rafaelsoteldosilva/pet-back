# api/infrastructure/events/handlers/pet.py

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import FieldDoesNotExist
from django.db import transaction

from api.infrastructure.events.dispatcher import register
from api.infrastructure.events.types import EVENT_CLINICAL_EVENT_OCCURRED
from api.infrastructure.orm.models.pet import Pet


DRAFT_RECORD_STATUS = "DRAFT"
CLINICAL_RECORD_STATUS = "CLINICAL"
ARCHIVED_RECORD_STATUS = "ARCHIVED"


def _normalize_record_status(value: Any) -> str:
    return str(value or "").strip().upper()


def _pet_model_has_field(field_name: str) -> bool:
    try:
        Pet._meta.get_field(field_name)
    except FieldDoesNotExist:
        return False

    return True


def _get_pet_id_from_event(event: dict[str, Any]) -> int:
    pet_id = event.get("pet_id")

    if pet_id is not None:
        return int(pet_id)

    pet = event.get("pet")

    if isinstance(pet, Pet):
        return int(cast(int, pet.pk))

    raise ValueError(
        "Clinical event payload must include either 'pet_id' or 'pet'."
    )


@transaction.atomic
def handle_pet_clinical_event(event: dict[str, Any]) -> None:
    """
    Reacts to a clinical event and promotes the pet record from DRAFT to CLINICAL.

    This handler intentionally does not create the clinical event. It only reacts
    after another part of the system emits EVENT_CLINICAL_EVENT_OCCURRED.
    """

    pet_id = _get_pet_id_from_event(event)

    try:
        pet = Pet.objects.select_for_update().get(pk=pet_id)
    except Pet.DoesNotExist:
        return

    current_record_status = _normalize_record_status(
        getattr(pet, "clinical_record_status", None)
    )

    if current_record_status == CLINICAL_RECORD_STATUS:
        return

    if current_record_status == ARCHIVED_RECORD_STATUS:
        return

    if current_record_status != DRAFT_RECORD_STATUS:
        return

    pet.clinical_record_status = CLINICAL_RECORD_STATUS

    update_fields = {"clinical_record_status"}

    if _pet_model_has_field("updated_at"):
        update_fields.add("updated_at")

    pet.save(update_fields=sorted(update_fields))


register(
    EVENT_CLINICAL_EVENT_OCCURRED,
    handle_pet_clinical_event,
)


__all__ = [
    "handle_pet_clinical_event",
]