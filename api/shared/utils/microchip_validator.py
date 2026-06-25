
# api/shared/utils/microchip_validator.py

import re

from django.core.exceptions import ValidationError

def microchip_validator(value: str | None) -> None:
    if value in (None, ""):
        return

    val = str(value).strip()

    if not re.fullmatch(r"\d{15}", val):
        raise ValidationError(
            "El código de microchip debe contener exactamente 15 dígitos numéricos."
        )