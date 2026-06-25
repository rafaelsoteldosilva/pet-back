# api/shared/orm/audit_mixins.py

from __future__ import annotations

from typing import Any, cast

from django.core.exceptions import ValidationError


def _has_text_value(value: Any) -> bool:
    if value is None:
        return False

    if not isinstance(value, str):
        return bool(value)

    return bool(value.strip())


def _add_error(
    errors: dict[str, list[str]],
    field_name: str,
    message: str,
) -> None:
    if field_name not in errors:
        errors[field_name] = []

    errors[field_name].append(message)


def _raise_validation_errors(errors: dict[str, list[str]]) -> None:
    if errors:
        raise ValidationError(errors)


def _validate_timestamp_actor_reason_fields(
    *,
    model_self: Any,
    errors: dict[str, list[str]],
    timestamp_field: str,
    actor_field: str | None,
    reason_field: str | None,
    action_label: str,
    require_reason_when_timestamp_is_set: bool = True,
) -> None:
    timestamp_value = getattr(model_self, timestamp_field, None)
    has_timestamp = timestamp_value is not None

    actor_id: Any = None
    has_actor = False

    if actor_field is not None:
        actor_id = getattr(model_self, f"{actor_field}_id", None)
        has_actor = actor_id is not None

    reason_value: Any = None
    has_reason = False

    if reason_field is not None:
        reason_value = getattr(model_self, reason_field, None)
        has_reason = _has_text_value(reason_value)

    if has_actor and not has_timestamp:
        _add_error(
            errors,
            timestamp_field,
            (
                f"Debe indicar la fecha/hora de {action_label} si se indica "
                "quién realizó la acción."
            ),
        )

    if has_reason and not has_timestamp:
        _add_error(
            errors,
            timestamp_field,
            (
                f"Debe indicar la fecha/hora de {action_label} si se indica "
                "el motivo."
            ),
        )

    if (
        has_timestamp
        and require_reason_when_timestamp_is_set
        and reason_field is not None
        and not has_reason
    ):
        _add_error(
            errors,
            reason_field,
            f"Debe indicar el motivo de {action_label}.",
        )


def _validate_boolean_timestamp_actor_fields(
    *,
    model_self: Any,
    errors: dict[str, list[str]],
    boolean_field: str,
    timestamp_field: str,
    actor_field: str | None,
    action_label: str,
) -> None:
    boolean_value = bool(getattr(model_self, boolean_field, False))
    timestamp_value = getattr(model_self, timestamp_field, None)
    has_timestamp = timestamp_value is not None

    actor_id: Any = None
    has_actor = False

    if actor_field is not None:
        actor_id = getattr(model_self, f"{actor_field}_id", None)
        has_actor = actor_id is not None

    if boolean_value and not has_timestamp:
        _add_error(
            errors,
            timestamp_field,
            f"Debe indicar la fecha/hora cuando {action_label}.",
        )

    if not boolean_value and has_timestamp:
        _add_error(
            errors,
            timestamp_field,
            (
                f"No debe indicar fecha/hora de {action_label} si el estado "
                "no está marcado."
            ),
        )

    if not boolean_value and has_actor and actor_field is not None:
        _add_error(
            errors,
            actor_field,
            (
                f"No debe indicar quién realizó {action_label} si el estado "
                "no está marcado."
            ),
        )


class SoftDeleteAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for models that use soft delete audit fields.

    Expected model fields:
    - soft_deleted_at
    - soft_deleted_by

    Optional model fields:
    - delete_reason
    - is_active

    This mixin does not define the fields.
    The fields must be declared directly in the Django model.
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        soft_deleted_at = getattr(model_self, "soft_deleted_at", None)
        soft_deleted_by_id = getattr(model_self, "soft_deleted_by_id", None)
        is_active = getattr(model_self, "is_active", None)

        if soft_deleted_by_id is not None and soft_deleted_at is None:
            _add_error(
                errors,
                "soft_deleted_at",
                (
                    "Debe indicar la fecha de eliminación si se indica "
                    "quién eliminó el registro."
                ),
            )

        if soft_deleted_at is not None and is_active is True:
            _add_error(
                errors,
                "is_active",
                "Un registro eliminado no puede estar activo.",
            )

        if hasattr(model_self, "delete_reason"):
            _validate_timestamp_actor_reason_fields(
                model_self=model_self,
                errors=errors,
                timestamp_field="soft_deleted_at",
                actor_field="soft_deleted_by",
                reason_field="delete_reason",
                action_label="eliminación",
                require_reason_when_timestamp_is_set=True,
            )

        _raise_validation_errors(errors)


class DeactivationAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for models that use deactivation audit fields.

    Expected model fields:
    - deactivated_at
    - deactivated_by

    Optional model fields:
    - deactivation_reason
    - is_active

    This is useful for versioned records such as Campaign_Restriction_Set.
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        deactivated_at = getattr(model_self, "deactivated_at", None)
        deactivated_by_id = getattr(model_self, "deactivated_by_id", None)
        is_active = getattr(model_self, "is_active", None)

        if deactivated_by_id is not None and deactivated_at is None:
            _add_error(
                errors,
                "deactivated_at",
                (
                    "Debe indicar la fecha de desactivación si se indica "
                    "quién desactivó el registro."
                ),
            )

        if deactivated_at is not None and is_active is True:
            _add_error(
                errors,
                "is_active",
                "Un registro desactivado no puede estar activo.",
            )

        if hasattr(model_self, "deactivation_reason"):
            _validate_timestamp_actor_reason_fields(
                model_self=model_self,
                errors=errors,
                timestamp_field="deactivated_at",
                actor_field="deactivated_by",
                reason_field="deactivation_reason",
                action_label="desactivación",
                require_reason_when_timestamp_is_set=True,
            )

        _raise_validation_errors(errors)


class VoidAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for clinical voiding.

    Expected model fields:
    - voided_at
    - voided_by
    - void_reason

    Use this for clinical records that should remain in history but be marked
    as invalid, mistaken, or clinically voided.
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        _validate_timestamp_actor_reason_fields(
            model_self=model_self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
            reason_field="void_reason",
            action_label="anulación",
            require_reason_when_timestamp_is_set=True,
        )

        _raise_validation_errors(errors)


class CancellationAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for cancellation.

    Expected model fields:
    - cancelled_at
    - cancelled_by
    - cancel_reason

    Use this for appointments, consultations, follow-ups, or planned workflow
    records that were cancelled.
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        _validate_timestamp_actor_reason_fields(
            model_self=model_self,
            errors=errors,
            timestamp_field="cancelled_at",
            actor_field="cancelled_by",
            reason_field="cancel_reason",
            action_label="cancelación",
            require_reason_when_timestamp_is_set=True,
        )

        _raise_validation_errors(errors)


class DoneAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for records that have a done/done_at/done_by state.

    Expected model fields:
    - done
    - done_at

    Optional model field:
    - done_by
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        actor_field: str | None = None

        if hasattr(model_self, "done_by_id"):
            actor_field = "done_by"

        _validate_boolean_timestamp_actor_fields(
            model_self=model_self,
            errors=errors,
            boolean_field="done",
            timestamp_field="done_at",
            actor_field=actor_field,
            action_label="el registro está completado",
        )

        _raise_validation_errors(errors)


class AppliedAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for records that have is_applied/applied_at.

    Expected model fields:
    - is_applied
    - applied_at

    Optional model field:
    - applied_by
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        actor_field: str | None = None

        if hasattr(model_self, "applied_by_id"):
            actor_field = "applied_by"

        _validate_boolean_timestamp_actor_fields(
            model_self=model_self,
            errors=errors,
            boolean_field="is_applied",
            timestamp_field="applied_at",
            actor_field=actor_field,
            action_label="el registro está aplicado",
        )

        _raise_validation_errors(errors)


class ClosedAuditValidationMixin:
    """
    Pure mixin.
    Does not inherit from models.Model.

    Validates consistency for records that have is_closed/closed_at.

    Expected model fields:
    - is_closed
    - closed_at

    Optional model field:
    - closed_by
    """

    def clean(self) -> None:
        super_clean = cast(Any, super()).clean
        super_clean()

        model_self = cast(Any, self)
        errors: dict[str, list[str]] = {}

        actor_field: str | None = None

        if hasattr(model_self, "closed_by_id"):
            actor_field = "closed_by"

        _validate_boolean_timestamp_actor_fields(
            model_self=model_self,
            errors=errors,
            boolean_field="is_closed",
            timestamp_field="closed_at",
            actor_field=actor_field,
            action_label="el registro está cerrado",
        )

        _raise_validation_errors(errors)


__all__ = [
    "SoftDeleteAuditValidationMixin",
    "DeactivationAuditValidationMixin",
    "VoidAuditValidationMixin",
    "CancellationAuditValidationMixin",
    "DoneAuditValidationMixin",
    "AppliedAuditValidationMixin",
    "ClosedAuditValidationMixin",
]