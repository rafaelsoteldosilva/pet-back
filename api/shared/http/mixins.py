# api/shared/http/mixins.py

from django.db import models


class TrimFieldsMixin:
    """
    Mixin puro. NO hereda de models.Model.
    Compatible con cualquier Django model.
    """

    def trim_charfields(self):
        for field in self._meta.concrete_fields:  # type: ignore[attr-defined]
            if isinstance(field, (models.CharField, models.TextField)):
                value = getattr(self, field.name, None)
                if isinstance(value, str):
                    setattr(self, field.name, value.strip())

    def clean(self):
        super().clean()  # type: ignore[misc]
        self.trim_charfields()
