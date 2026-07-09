# api/domains/pet/microchip_policy.py

from __future__ import annotations

from datetime import date

from api.domains.pet.errors import (
    PetMicrochipCode15DigitsNotApplicableError,
    PetMicrochipCodeRequiresMicrochipCodeError,
    PetMicrochipDateBeforeBirthDateError,
)


def validate_pet_microchip_code_consistency_with_has_microchip(
    *,
    has_microchip: bool,
    microchip_code: str | None,
) -> None:
    """
    Enforces that microchip_code only has meaningful content when the pet has a
    microchip.
    """

    if has_microchip:
        return

    if microchip_code is None:
        return

    if microchip_code.strip() == "":
        return

    raise PetMicrochipCodeRequiresMicrochipCodeError(
        "If has_microchip is false, microchip_code must be null or empty."
    )


def validate_pet_microchip_code_15_digits_consistency_with_has_microchip(
    *,
    has_microchip: bool,
    microchip_code_is_15_digits: bool | None,
) -> None:
    """
    Enforces consistency between has_microchip and microchip_code_is_15_digits.

    Rules enforced:
    - If microchip_code_is_15_digits is None, the rule does nothing.
      This means ISO 11784 compliance is unknown or not applicable.
    - If microchip_code_is_15_digits is True or False, then the pet must have a
      microchip.
    """

    if microchip_code_is_15_digits is None:
        return

    if has_microchip:
        return

    raise PetMicrochipCode15DigitsNotApplicableError(
        "If microchip_code_is_15_digits is true or false, "
        "has_microchip must be true."
    )


def validate_pet_microchip_date_not_before_birth_date(
    *,
    birth_date: date | None,
    microchip_date: date | None,
) -> None:
    """
    Enforces that the microchip implantation date cannot be before the pet's
    birth date.

    If either date is missing, the rule does nothing.
    """

    if birth_date is None:
        return

    if microchip_date is None:
        return

    if microchip_date < birth_date:
        raise PetMicrochipDateBeforeBirthDateError(
            "microchip_date cannot be before birth_date."
        )


__all__ = [
    "validate_pet_microchip_code_consistency_with_has_microchip",
    "validate_pet_microchip_code_15_digits_consistency_with_has_microchip",
    "validate_pet_microchip_date_not_before_birth_date",
]