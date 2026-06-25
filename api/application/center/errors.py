# api/application/center/errors.py

from __future__ import annotations


class VeterinaryCenterNotFoundError(Exception):
    pass


class CenterContactNotFoundError(Exception):
    pass


class CenterContactHasPetContactLinksError(Exception):
    def __init__(
        self,
        *,
        pet_names: list[str],
        total_linked_pets: int,
    ) -> None:
        self.pet_names = pet_names
        self.total_linked_pets = total_linked_pets

        super().__init__(
            "Center contact cannot be deleted because it has pet links."
        )


__all__ = [
    "VeterinaryCenterNotFoundError",
    "CenterContactNotFoundError",
    "CenterContactHasPetContactLinksError",
]