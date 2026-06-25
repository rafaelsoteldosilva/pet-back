# api/shared/orm/mixins.py

from __future__ import annotations

from typing import Any, cast

from django.db import models


class FullCleanOnSaveMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Ensures model validation runs before normal model.save().

    This runs:
    - field validation
    - model.clean()
    - unique validation
    - model constraints validation

    Important:
    This affects normal .save().
    It does not affect QuerySet.update(), bulk_create(), bulk_update(), or raw SQL.
    """

    def save(self, *args: Any, **kwargs: Any) -> None:
        model_self = cast(models.Model, self)
        model_self.full_clean()

        super_save = cast(Any, super()).save
        super_save(*args, **kwargs)


class TrimFieldsMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    It trims CharField and TextField values when model.clean() runs.

    If the model also uses FullCleanOnSaveMixin, this trimming will run
    automatically before normal model.save().
    """

    def trim_charfields(self) -> None:
        model_self = cast(Any, self)

        for field in model_self._meta.concrete_fields:
            if isinstance(field, (models.CharField, models.TextField)):
                value = getattr(self, field.name, None)

                if isinstance(value, str):
                    setattr(self, field.name, value.strip())

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        self.trim_charfields()


__all__ = [
    "FullCleanOnSaveMixin",
    "TrimFieldsMixin",
]