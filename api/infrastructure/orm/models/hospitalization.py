# api/infrastructure/orm/models/hospitalization.py

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from api.shared.choices.choices import (
    Choices_Hospitalization_Status_Choices,
    Choices_Resource_Types,
)
from api.shared.constants.constants import (
    CENTER_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    CENTER_HOSPITALIZATION_UNITS_RN,
    CENTER_HOSPITALIZATIONS_RN,
    CENTER_HOSPITALIZED_PET_DAILY_RECORDS_RN,
    CENTER_STAFF_MEMBER_MODEL,
    CONSULTATION_HOSPITALIZATIONS_RN,
    CONSULTATION_MODEL,
    HOSPITALIZATION_ACTIVE_CANNOT_HAVE_DISCHARGED_AT,
    HOSPITALIZATION_DECEASED_REQUIRES_TIMESTAMP,
    HOSPITALIZATION_DISCHARGED_REQUIRES_TIMESTAMP,
    HOSPITALIZATION_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    HOSPITALIZATION_MODEL,
    HOSPITALIZATION_PET_DAILY_RECORDS_RN,
    HOSPITALIZATION_UNIT_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    HOSPITALIZATION_UNIT_MODEL,
    IDX_ACTIVE_HOSPITALIZATION_PER_PET,
    IDX_DAILY_RECORD_CENTER_DATETIME,
    IDX_DAILY_RECORD_HOSPITALIZATION_DATETIME,
    IDX_HOSPITALIZATION_CENTER_ADMITTED,
    IDX_HOSPITALIZATION_PET_STATUS,
    IDX_HOSPITALIZATION_STATUS_CENTER,
    IDX_HOSPITALIZATION_UNIT_CENTER_ACTIVE,
    IDX_UNIT_ASSIGNMNT_CTRE_ACT,
    IDX_UNIT_ASSIGNMT_HOSP,
    PET_HOSPITALIZATIONS_RN,
    PET_MODEL,
    UNIQUE_ACTIVE_ASSIGNMENT_PER_HOSPITALIZATION,
    UNIQUE_ACTIVE_ASSIGNMENT_PER_UNIT,
    UNIQUE_ACTIVE_HOSPITALIZATION_PER_PET,
    UNIQUE_BED_CODE_PER_CENTER,
    UNIQUE_DAILY_RECORD_PER_HOSPITALIZATION_DATETIME,
    VETERINARY_CENTER_MODEL,
)
from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin


# Models located in api/infrastructure/orm/models/hospitalization.py:
# Hospitalization
# Hospitalization_Unit
# Hospitalization_Unit_Assignment
# Hospitalized_Pet_Daily_Record


def _add_error(
    errors: dict[str, list[str]],
    field_name: str,
    message: str,
) -> None:
    if field_name not in errors:
        errors[field_name] = []

    errors[field_name].append(message)


def _raise_errors(errors: dict[str, list[str]]) -> None:
    if errors:
        raise ValidationError(errors)


def _clean_string(value: object) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _get_related_object(
    *,
    instance: models.Model,
    related_field_name: str,
) -> object | None:
    related_id = getattr(instance, f"{related_field_name}_id", None)

    if related_id is None:
        return None

    try:
        return getattr(instance, related_field_name)
    except Exception:
        return None


def _validate_related_object_belongs_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    related_field_name: str,
    center_field_name: str = "veterinary_center",
) -> None:
    center_id = getattr(instance, f"{center_field_name}_id", None)

    if center_id is None:
        return

    related_id = getattr(instance, f"{related_field_name}_id", None)

    if related_id is None:
        return

    related_object = _get_related_object(
        instance=instance,
        related_field_name=related_field_name,
    )

    if related_object is None:
        return

    related_center_id = getattr(related_object, "veterinary_center_id", None)

    if related_center_id is None:
        return

    if int(related_center_id) != int(center_id):
        _add_error(
            errors,
            related_field_name,
            f"{related_field_name} must belong to the same veterinary center.",
        )


def _validate_actor_requires_timestamp(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    timestamp_field: str,
    actor_field: str,
) -> None:
    timestamp_value = getattr(instance, timestamp_field, None)
    actor_id = getattr(instance, f"{actor_field}_id", None)

    if actor_id is not None and timestamp_value is None:
        _add_error(
            errors,
            timestamp_field,
            f"{timestamp_field} is required when {actor_field} is set.",
        )


def _validate_timestamp_requires_actor(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    timestamp_field: str,
    actor_field: str,
) -> None:
    timestamp_value = getattr(instance, timestamp_field, None)
    actor_id = getattr(instance, f"{actor_field}_id", None)

    if timestamp_value is not None and actor_id is None:
        _add_error(
            errors,
            actor_field,
            f"{actor_field} is required when {timestamp_field} is set.",
        )


def _validate_audit_actors_belong_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
) -> None:
    for actor_field_name in (
        "created_by",
        "discharged_by",
        "voided_by",
        "soft_deleted_by",
    ):
        if not hasattr(instance, f"{actor_field_name}_id"):
            continue

        _validate_related_object_belongs_to_center(
            instance=instance,
            errors=errors,
            related_field_name=actor_field_name,
        )


class Hospitalization(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Representa un evento de hospitalización de un paciente.

    Un paciente puede tener múltiples hospitalizaciones a lo largo del tiempo.
    La ocupación de unidades se controla mediante Hospitalization_Unit_Assignment.

    Aggregate root clínico que encapsula el ciclo completo de hospitalización.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_HOSPITALIZATIONS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_HOSPITALIZATIONS_RN,
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CONSULTATION_HOSPITALIZATIONS_RN,
        help_text="Consulta que originó la hospitalización",
    )

    admitted_at = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de ingreso",
    )

    discharged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de alta",
    )

    discharged_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    deceased_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de fallecimiento",
    )

    reason = models.TextField(
        help_text="Motivo clínico de hospitalización",
    )

    status = models.CharField(
        max_length=20,
        choices=Choices_Hospitalization_Status_Choices.choices,
        default=Choices_Hospitalization_Status_Choices.STATUS_ACTIVE,
    )

    notes = models.TextField(
        blank=True,
        help_text="Notas clínicas adicionales",
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    void_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        pet_id: int
        consultation_id: int | None
        created_by_id: int | None
        discharged_by_id: int | None
        voided_by_id: int | None

    class Meta:
        ordering = ["-admitted_at"]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        status=Choices_Hospitalization_Status_Choices.STATUS_DISCHARGED,
                        discharged_at__isnull=False,
                    )
                    | ~Q(
                        status=Choices_Hospitalization_Status_Choices.STATUS_DISCHARGED,
                    )
                ),
                name=HOSPITALIZATION_DISCHARGED_REQUIRES_TIMESTAMP,
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=Choices_Hospitalization_Status_Choices.STATUS_DECEASED,
                        deceased_at__isnull=False,
                    )
                    | ~Q(
                        status=Choices_Hospitalization_Status_Choices.STATUS_DECEASED,
                    )
                ),
                name=HOSPITALIZATION_DECEASED_REQUIRES_TIMESTAMP,
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=Choices_Hospitalization_Status_Choices.STATUS_ACTIVE,
                        discharged_at__isnull=True,
                    )
                    | ~Q(
                        status=Choices_Hospitalization_Status_Choices.STATUS_ACTIVE,
                    )
                ),
                name=HOSPITALIZATION_ACTIVE_CANNOT_HAVE_DISCHARGED_AT,
            ),
            models.UniqueConstraint(
                fields=["pet"],
                condition=Q(
                    status=Choices_Hospitalization_Status_Choices.STATUS_ACTIVE,
                    voided_at__isnull=True,
                ),
                name=UNIQUE_ACTIVE_HOSPITALIZATION_PER_PET,
            ),
        ]

        indexes = [
            models.Index(
                fields=["pet", "status"],
                name=IDX_HOSPITALIZATION_PET_STATUS,
            ),
            models.Index(
                fields=["veterinary_center", "-admitted_at"],
                name=IDX_HOSPITALIZATION_CENTER_ADMITTED,
            ),
            models.Index(
                fields=["status", "veterinary_center"],
                name=IDX_HOSPITALIZATION_STATUS_CENTER,
            ),
            models.Index(
                fields=["pet"],
                condition=Q(
                    status=Choices_Hospitalization_Status_Choices.STATUS_ACTIVE,
                    voided_at__isnull=True,
                ),
                name=IDX_ACTIVE_HOSPITALIZATION_PER_PET,
            ),
        ]

    @property
    def is_active(self) -> bool:
        return (
            self.status == Choices_Hospitalization_Status_Choices.STATUS_ACTIVE
            and self.voided_at is None
        )

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.reason = _clean_string(self.reason)
        self.notes = _clean_string(self.notes)
        self.void_reason = _clean_string(self.void_reason)

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="discharged_at",
            actor_field="discharged_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="discharged_at",
            actor_field="discharged_by",
        )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
        )

        if self.consultation_id and self.pet_id:
            consultation = _get_related_object(
                instance=self,
                related_field_name="consultation",
            )

            consultation_pet_id = getattr(consultation, "pet_id", None)

            if consultation_pet_id is not None and int(consultation_pet_id) != int(self.pet_id):
                _add_error(
                    errors,
                    "consultation",
                    "Consultation must belong to the same pet.",
                )

        if self.pk:
            old = Hospitalization.objects.only("pet_id").get(pk=self.pk)

            if old.pet_id != self.pet_id:
                _add_error(
                    errors,
                    "pet",
                    "Pet cannot be changed once hospitalized.",
                )

        if not self.reason:
            _add_error(
                errors,
                "reason",
                "Hospitalization reason is required.",
            )

        if (
            self.discharged_at is not None
            and self.admitted_at is not None
            and self.discharged_at < self.admitted_at
        ):
            _add_error(
                errors,
                "discharged_at",
                "discharged_at cannot be before admitted_at.",
            )

        if (
            self.deceased_at is not None
            and self.admitted_at is not None
            and self.deceased_at < self.admitted_at
        ):
            _add_error(
                errors,
                "deceased_at",
                "deceased_at cannot be before admitted_at.",
            )

        if (
            self.status == Choices_Hospitalization_Status_Choices.STATUS_DECEASED
            and not self.deceased_at
        ):
            _add_error(
                errors,
                "deceased_at",
                "deceased_at is required when status is DECEASED.",
            )

        if (
            self.status == Choices_Hospitalization_Status_Choices.STATUS_DISCHARGED
            and not self.discharged_at
        ):
            _add_error(
                errors,
                "discharged_at",
                "discharged_at is required when status is DISCHARGED.",
            )

        if (
            self.status != Choices_Hospitalization_Status_Choices.STATUS_DISCHARGED
            and self.discharged_at
        ):
            _add_error(
                errors,
                "discharged_at",
                "discharged_at must be null unless status is DISCHARGED.",
            )

        if (
            self.status != Choices_Hospitalization_Status_Choices.STATUS_DECEASED
            and self.deceased_at
        ):
            _add_error(
                errors,
                "deceased_at",
                "deceased_at must be null unless status is DECEASED.",
            )

        if (
            self.status == Choices_Hospitalization_Status_Choices.STATUS_ACTIVE
            and self.discharged_at
        ):
            _add_error(
                errors,
                "discharged_at",
                "ACTIVE hospitalization cannot have discharged_at.",
            )

        if self.voided_at and not self.void_reason:
            _add_error(
                errors,
                "void_reason",
                "void_reason is required when voided_at is set.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"Hospitalization {self.id} - Pet {self.pet_id}"


class Hospitalization_Unit(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Camas, jaulas, UCI, etc.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_HOSPITALIZATION_UNITS_RN,
    )

    code = models.CharField(
        max_length=20,
        help_text="Hospitalization Unit identifier, e.g. A1, ICU-2",
    )

    area = models.CharField(
        max_length=50,
        blank=True,
        help_text="Sector / room / ward",
    )

    is_active = models.BooleanField(
        default=True,
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    soft_deleted_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["code"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=Q(soft_deleted_at__isnull=True),
                name=UNIQUE_BED_CODE_PER_CENTER,
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active"],
                name=IDX_HOSPITALIZATION_UNIT_CENTER_ACTIVE,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _clean_string(self.code).upper()
        self.area = _clean_string(self.area)

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="soft_deleted_at",
            actor_field="soft_deleted_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="soft_deleted_at",
            actor_field="soft_deleted_by",
        )

        if not self.code:
            _add_error(
                errors,
                "code",
                "Hospitalization unit code is required.",
            )

        if self.soft_deleted_at is not None:
            self.is_active = False

        _raise_errors(errors)

    def __str__(self) -> str:
        if self.area:
            return f"{self.code} ({self.area})"

        return self.code


class Hospitalization_Unit_Assignment(
    TrimFieldsMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Asignación temporal de un paciente a una unidad.

    Aquí se controla que una unidad no pueda tener más de una asignación
    activa al mismo tiempo.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    )

    hospitalization = models.ForeignKey(
        HOSPITALIZATION_MODEL,
        on_delete=models.CASCADE,
        related_name=HOSPITALIZATION_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    )

    resource_type = models.CharField(
        max_length=20,
        choices=Choices_Resource_Types.choices,
        default=Choices_Resource_Types.CAGE,
    )

    hospitalization_unit = models.ForeignKey(
        HOSPITALIZATION_UNIT_MODEL,
        on_delete=models.PROTECT,
        related_name=HOSPITALIZATION_UNIT_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    )

    assigned_at = models.DateTimeField(
        default=timezone.now,
    )

    released_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    void_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        hospitalization_id: int
        hospitalization_unit_id: int
        created_by_id: int | None
        voided_by_id: int | None

    class Meta:
        ordering = ["-assigned_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["hospitalization"],
                condition=Q(
                    released_at__isnull=True,
                    voided_at__isnull=True,
                ),
                name=UNIQUE_ACTIVE_ASSIGNMENT_PER_HOSPITALIZATION,
            ),
            models.UniqueConstraint(
                fields=["hospitalization_unit"],
                condition=Q(
                    released_at__isnull=True,
                    voided_at__isnull=True,
                ),
                name=UNIQUE_ACTIVE_ASSIGNMENT_PER_UNIT,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "released_at"],
                name=IDX_UNIT_ASSIGNMNT_CTRE_ACT,
            ),
            models.Index(
                fields=["hospitalization"],
                name=IDX_UNIT_ASSIGNMT_HOSP,
            ),
        ]

    @property
    def is_active(self) -> bool:
        return self.released_at is None and self.voided_at is None

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.void_reason = _clean_string(self.void_reason)

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="hospitalization",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="hospitalization_unit",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
        )

        if (
            self.assigned_at
            and self.released_at
            and self.released_at < self.assigned_at
        ):
            _add_error(
                errors,
                "released_at",
                "released_at cannot be before assigned_at.",
            )

        if self.voided_at and not self.void_reason:
            _add_error(
                errors,
                "void_reason",
                "void_reason is required when voided_at is set.",
            )

        if self.is_active and self.hospitalization_id:
            hospitalization = _get_related_object(
                instance=self,
                related_field_name="hospitalization",
            )

            hospitalization_is_active = getattr(
                hospitalization,
                "is_active",
                None,
            )

            if hospitalization_is_active is False:
                _add_error(
                    errors,
                    "hospitalization",
                    (
                        "Cannot create an active unit assignment for an inactive "
                        "hospitalization."
                    ),
                )

        if self.is_active and self.hospitalization_unit_id:
            hospitalization_unit = _get_related_object(
                instance=self,
                related_field_name="hospitalization_unit",
            )

            unit_is_active = getattr(
                hospitalization_unit,
                "is_active",
                None,
            )

            unit_soft_deleted_at = getattr(
                hospitalization_unit,
                "soft_deleted_at",
                None,
            )

            if unit_is_active is False:
                _add_error(
                    errors,
                    "hospitalization_unit",
                    "Cannot assign a patient to an inactive hospitalization unit.",
                )

            if unit_soft_deleted_at is not None:
                _add_error(
                    errors,
                    "hospitalization_unit",
                    "Cannot assign a patient to a deleted hospitalization unit.",
                )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"{self.hospitalization_id} → {self.hospitalization_unit_id}"


class Hospitalized_Pet_Daily_Record(
    TrimFieldsMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Snapshot clínico inmutable del paciente durante una hospitalización.

    Representa el estado clínico en un punto específico del tiempo.
    """

    hospitalization = models.ForeignKey(
        HOSPITALIZATION_MODEL,
        on_delete=models.CASCADE,
        related_name=HOSPITALIZATION_PET_DAILY_RECORDS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_HOSPITALIZED_PET_DAILY_RECORDS_RN,
    )

    recorded_at = models.DateTimeField(
        default=timezone.now,
    )

    notes = models.TextField(
        blank=True,
    )

    vital_signs_snapshot = models.JSONField(
        blank=True,
        null=True,
        help_text="Snapshot estructurado de signos vitales en este momento",
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    void_reason = models.CharField(
        max_length=255,
        blank=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        id: int
        hospitalization_id: int
        veterinary_center_id: int
        created_by_id: int | None
        voided_by_id: int | None

    class Meta:
        ordering = ["recorded_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["hospitalization", "recorded_at"],
                condition=Q(voided_at__isnull=True),
                name=UNIQUE_DAILY_RECORD_PER_HOSPITALIZATION_DATETIME,
            )
        ]

        indexes = [
            models.Index(
                fields=["hospitalization", "recorded_at"],
                name=IDX_DAILY_RECORD_HOSPITALIZATION_DATETIME,
            ),
            models.Index(
                fields=["veterinary_center", "recorded_at"],
                name=IDX_DAILY_RECORD_CENTER_DATETIME,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.notes = _clean_string(self.notes)
        self.void_reason = _clean_string(self.void_reason)

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="hospitalization",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="voided_at",
            actor_field="voided_by",
        )

        hospitalization = _get_related_object(
            instance=self,
            related_field_name="hospitalization",
        )

        admitted_at = getattr(hospitalization, "admitted_at", None)
        discharged_at = getattr(hospitalization, "discharged_at", None)
        deceased_at = getattr(hospitalization, "deceased_at", None)
        hospitalization_voided_at = getattr(hospitalization, "voided_at", None)

        if (
            self.recorded_at is not None
            and admitted_at is not None
            and self.recorded_at < admitted_at
        ):
            _add_error(
                errors,
                "recorded_at",
                "recorded_at cannot be before hospitalization admitted_at.",
            )

        if (
            self.recorded_at is not None
            and discharged_at is not None
            and self.recorded_at > discharged_at
        ):
            _add_error(
                errors,
                "recorded_at",
                "recorded_at cannot be after hospitalization discharged_at.",
            )

        if (
            self.recorded_at is not None
            and deceased_at is not None
            and self.recorded_at > deceased_at
        ):
            _add_error(
                errors,
                "recorded_at",
                "recorded_at cannot be after hospitalization deceased_at.",
            )

        if hospitalization_voided_at is not None and self.voided_at is None:
            _add_error(
                errors,
                "hospitalization",
                "Cannot create an active daily record for a voided hospitalization.",
            )

        if self.voided_at and not self.void_reason:
            _add_error(
                errors,
                "void_reason",
                "void_reason is required when voided_at is set.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"Daily record {self.hospitalization_id} @ {self.recorded_at}"


__all__ = [
    "Hospitalization",
    "Hospitalization_Unit",
    "Hospitalization_Unit_Assignment",
    "Hospitalized_Pet_Daily_Record",
]