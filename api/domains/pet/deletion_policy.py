# api/domains/pet/deletion_policy.py

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from api.domains.pet.errors import (
    PetCannotBeDeletedBecauseClinicalRecordsExistError,
    PetCannotBeDeletedByDifferentUserError,
)


@dataclass(frozen=True)
class PetDeletionContext:
    clinical_record_sources: tuple[str, ...]
    actor_user_id: int
    pet_created_by_user_id: int | None


PetDeletionRule = Callable[[PetDeletionContext], None]


def _normalize_strings(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(value).strip()
                for value in values
                if str(value).strip()
            }
        )
    )


def ensure_pet_has_no_clinical_records(
    context: PetDeletionContext,
) -> None:
    """
    A pet can be deleted only when it has no clinical records.
    """

    if not context.clinical_record_sources:
        return

    raise PetCannotBeDeletedBecauseClinicalRecordsExistError(
        clinical_record_sources=context.clinical_record_sources,
    )


def ensure_pet_was_created_by_actor(
    context: PetDeletionContext,
) -> None:
    """
    A pet can be deleted only by the same user who created it.
    """

    if context.pet_created_by_user_id is None:
        raise PetCannotBeDeletedByDifferentUserError()

    if int(context.actor_user_id) != int(context.pet_created_by_user_id):
        raise PetCannotBeDeletedByDifferentUserError()


PET_DELETION_RULES: tuple[PetDeletionRule, ...] = (
    ensure_pet_has_no_clinical_records,
    ensure_pet_was_created_by_actor,
)


def ensure_pet_can_be_deleted(
    *,
    clinical_record_sources: Iterable[str],
    actor_user_id: int,
    pet_created_by_user_id: int | None,
) -> None:
    """
    Enforces whether a Pet can be deleted.

    Domain rules:
    - A pet can be deleted only when it has no clinical records.
    - A pet can be deleted only by the same user who created it.

    This function receives already-calculated facts from the application layer.
    It must not import Django ORM models and must not query the database.
    """

    context = PetDeletionContext(
        clinical_record_sources=_normalize_strings(clinical_record_sources),
        actor_user_id=int(actor_user_id),
        pet_created_by_user_id=pet_created_by_user_id,
    )

    for rule in PET_DELETION_RULES:
        rule(context)


__all__ = [
    "PetDeletionContext",
    "PetDeletionRule",
    "ensure_pet_has_no_clinical_records",
    "ensure_pet_was_created_by_actor",
    "PET_DELETION_RULES",
    "ensure_pet_can_be_deleted",
]