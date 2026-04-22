
# api/shared/utils/microchip_validator.py

from django.core.exceptions import ValidationError

def microchip_validator(value: str):
    val = value.strip().upper() if value else ""
    if val.isdigit():
        if not (10 <= len(val) <= 15):
            raise ValidationError("ISO chips must be 10–15 digits.")
    elif not val.isalnum() or len(val) > 30:
        raise ValidationError("Alphanumeric microchips max length is 30.")