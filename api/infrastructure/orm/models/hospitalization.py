# api/infrastructure/orm/models/hospitalization.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import TYPE_CHECKING, Any
from django.db.models import Q

from api.shared.choices.choices import (
    Choices_HospitalizationStatusChoices,
    Choices_ResourceTypes,
)

from api.shared.constants.constants import *

from api.shared.http.mixins import TrimFieldsMixin

# Models located in api/infrastructure/orm/models/hospitalization.py:
# Models: Hospitalization, Hospitalization_Unit, Hospitalization_Unit_Assignment,
# Models: Hospitalized_Pet_Daily_Record,
class Hospitalization(models.Model):
    """
    Propósito: Representa un evento de hospitalización de un paciente.
    Un paciente puede tener múltiples hospitalizaciones a lo largo del tiempo,
    pero solo una activa simultáneamente.

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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CONSULTATION_HOSPITALIZATIONS_RN,
        help_text="Consulta que originó la hospitalización",
    )
    admitted_at = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de ingreso"
    )
    discharged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de alta"
    )
    deceased_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha y hora de fallecimiento"
    )
    reason = models.TextField(
        help_text="Motivo clínico de hospitalización"
    )
    status = models.CharField(
        max_length=20,
        choices=Choices_HospitalizationStatusChoices.choices,
        default=Choices_HospitalizationStatusChoices.STATUS_ACTIVE,
    )
    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CREATED_BY_HOSPITALIZATIONS_RN,
    )
    discharged_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=DISCHARGED_BY_HOSPITALIZATIONS_RN,
    )
    notes = models.TextField(
        blank=True,
        help_text="Notas clínicas adicionales"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        pet_id: int

    class Meta:
        ordering = ["-admitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["pet"],
                condition=Q(
                    status=Choices_HospitalizationStatusChoices.STATUS_ACTIVE
                ),
                name=UNIQUE_ACTIVE_HOSPITALIZATION_PER_UNIT,
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=Choices_HospitalizationStatusChoices.STATUS_DISCHARGED,
                        discharged_at__isnull=False,
                    )
                    |
                    ~Q(
                        status=Choices_HospitalizationStatusChoices.STATUS_DISCHARGED
                    )
                ),
                name=HOSPITALIZATION_DISCHARGED_REQUIRES_TIMESTAMP,
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=Choices_HospitalizationStatusChoices.STATUS_DECEASED,
                        deceased_at__isnull=False,
                    )
                    |
                    ~Q(
                        status=Choices_HospitalizationStatusChoices.STATUS_DECEASED
                    )
                ),
                name=HOSPITALIZATION_DISEASED_REQUIRES_TIMESTAMP,
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status=Choices_HospitalizationStatusChoices.STATUS_ACTIVE,
                        discharged_at__isnull=True,
                    )
                    |
                    ~Q(
                        status=Choices_HospitalizationStatusChoices.STATUS_ACTIVE
                    )
                ),
                name=HOSPITALIZATION_ACTIVE_CANNOT_HAVE_DISCHARGED_AT,
            ),
        ]
        indexes = [
            # búsqueda por paciente y estado
            models.Index(
                fields=["pet", "status"],
                name=IDX_HOSPITALIZATION_PET_STATUS
            ),
            # timeline por centro
            models.Index(
                fields=["veterinary_center", "-admitted_at"],
                name=IDX_HOSPITALIZATION_CENTER_ADMITTED
            ),
            # dashboard hospitalizaciones activas
            models.Index(
                fields=["status", "veterinary_center"],
                name=IDX_HOSPITALIZATION_STATUS_CENTER
            ),
            # lookup ultra rápido de hospitalización activa
            models.Index(
                fields=["pet"],
                condition=Q(
                    status=Choices_HospitalizationStatusChoices.STATUS_ACTIVE
                ),
                name=IDX_ACTIVE_HOSPITALIZATION_PER_PET
            ),
        ]

    def __str__(self):
        return f"Hospitalization {self.id} - Pet {self.pet_id}"

    @property
    def is_active(self) -> bool:
        return (
            self.status ==
            Choices_HospitalizationStatusChoices.STATUS_ACTIVE
        )

    def clean(self):
        super().clean()

        # Multi-tenant safety
        if self.pet_id and self.veterinary_center_id:
            if self.pet.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    "Pet must belong to the same veterinary_center."
                )
        # Prevent changing pet after creation
        if self.pk:
            old = Hospitalization.objects.get(pk=self.pk)
            if old.pet_id != self.pet_id:
                raise ValidationError(
                    "Pet cannot be changed once hospitalized."
                )
        # Logical validations
        if (
            self.status ==
            Choices_HospitalizationStatusChoices.STATUS_DECEASED
            and not self.deceased_at
        ):
            raise ValidationError(
                "deceased_at is required when status is DECEASED."
            )
        if (
            self.status ==
            Choices_HospitalizationStatusChoices.STATUS_DISCHARGED
            and not self.discharged_at
        ):
            raise ValidationError(
                "discharged_at is required when status is DISCHARGED."
            )
        if (
            self.status ==
            Choices_HospitalizationStatusChoices.STATUS_ACTIVE
            and self.discharged_at
        ):
            raise ValidationError(
                "ACTIVE hospitalization cannot have discharged_at."
            )
        if (
            self.status !=
            Choices_HospitalizationStatusChoices.STATUS_DECEASED
            and self.deceased_at
        ):
            raise ValidationError(
                "deceased_at must be null unless status is DECEASED."
            )

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)


class Hospitalization_Unit(models.Model):
    """
    Propósito: Camas, jaulas, UCI, etc.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_HOSPITALIZATION_UNITS_RN,
    )
    code = models.CharField(
        max_length=20,
        help_text="Hospitalization Unit identifier (e.g. A1, ICU-2)"
    )
    area = models.CharField(
        max_length=50,
        blank=True,
        help_text="Sector / room / ward"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                name=UNIQUE_BED_CODE_PER_CENTER,
            )
        ]
        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active"],
                name=IDX_HOSPITALIZATION_UNIT_CENTER_ACTIVE
            ),
        ]

    def save(self, *args: Any, **kwargs: Any):

        if self.code:
            self.code = self.code.strip().upper()

        if self.area:
            self.area = self.area.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.area})"


class Hospitalization_Unit_Assignment(models.Model):
    """
    Propósito: Asignación temporal de un paciente a una unidad.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    )
    hospitalization = models.ForeignKey(
        HOSPITALIZATION_MODEL,
        on_delete=models.CASCADE,
        related_name=HOSPITALIZATION_UNIT_ASSIGNMENTS_RN,
    )
    resource_type = models.CharField(
        max_length=20,
        choices=Choices_ResourceTypes.choices,
        default=Choices_ResourceTypes.CAGE,
    )
    hospitalization_unit = models.ForeignKey(
        HOSPITALIZATION_UNIT_MODEL,
        on_delete=models.PROTECT,
        related_name=HOSPITALIZATION_UNIT_ASSIGMENTS_RN,
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        hospitalization_id: int
        hospitalization_unit_id: int

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["hospitalization"],
                condition=Q(released_at__isnull=True),
                name=UNIQUE_ACTIVE_ASSIGNMENT_PER_HOSPITALIZATION,
            ),
            models.UniqueConstraint(
                fields=["hospitalization_unit"],
                condition=Q(released_at__isnull=True),
                name=UNIQUE_ACTIVE_ASSIGNMENT_PER_UNIT,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "released_at"],
                name=IDX_UNIT_ASSIGMENT_CENTER_ACTIVE
            ),
            models.Index(
                fields=["hospitalization"],
                name=IDX_UNIT_ASSIGMENT_HOSPITALIZATION
            ),
        ]

    def clean(self):
        if self.released_at and self.released_at < self.assigned_at:
            raise ValidationError(
                "released_at cannot be before assigned_at."
            )
        if (
            self.hospitalization_unit_id and
            self.veterinary_center_id and
            self.hospitalization_unit.veterinary_center_id != self.veterinary_center_id
        ):
            raise ValidationError(
                "hospitalization_unit must belong to the same veterinary_center."
            )
        if (
            self.hospitalization_id and
            self.veterinary_center_id and
            self.hospitalization.veterinary_center_id != self.veterinary_center_id
        ):
            raise ValidationError(
                "hospitalization must belong to the same veterinary_center."
            )

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hospitalization_id} → {self.hospitalization_unit_id}"
    
class Hospitalized_Pet_Daily_Record(TrimFieldsMixin, models.Model):
    """
    Propósito: Snapshot clínico inmutable del paciente durante una hospitalización.
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

    recorded_at = models.DateTimeField(default=timezone.now)

    notes = models.TextField(blank=True)

    vital_signs_snapshot = models.JSONField(
        blank=True,
        null=True,
        help_text="Snapshot estructurado de signos vitales en este momento"
    )

    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CREATED_BY_HOSPITALIZED_PET_DAILY_RECORDS_RN,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    if TYPE_CHECKING:
        id: int
        hospitalization_id: int

    class Meta:
        ordering = ["recorded_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["hospitalization", "recorded_at"],
                name=UNIQUE_DAILY_RECORD_PER_HOSPITALIZATION_DATETIME
            )
        ]

        indexes = [
            models.Index(
                fields=["hospitalization", "recorded_at"],
                name=IDX_DAILY_RECORD_HOSPITALIZATION_DATETIME
            ),
            models.Index(
                fields=["veterinary_center", "recorded_at"],
                name=IDX_DAILY_RECORD_CENTER_DATETIME
            ),
        ]

    def __str__(self):
        return f"Daily record {self.hospitalization_id} @ {self.recorded_at}"
    
__all__ = [
    "Hospitalization", 
    "Hospitalization_Unit", 
    "Hospitalization_Unit_Assignment", 
    "Hospitalized_Pet_Daily_Record",
]
