
# api/infrastructure/events/handlers/pet.py

# Its purpose is to automatically react when a clinical event happens, and update the pet’s record 
# status if needed — without coupling that logic to the place where the event was created.

# This is a classic domain event handler.

from typing import Any

# from api.domain.pet.services import transition_pet_record_to_clinical_if_needed
from api.infrastructure.events.dispatcher import register
from api.infrastructure.events.types import EVENT_CLINICAL_EVENT_OCCURRED

# from api.infrastructure.orm.models.patient import Pet

def handle_pet_clinical_event(event: dict[str, Any]) -> None:
    pass
    # pet: Pet = event["pet"]
    # transition_pet_record_to_clinical_if_needed(pet)

register(
    EVENT_CLINICAL_EVENT_OCCURRED,
    handle_pet_clinical_event,
)
