
# api/infrastructure/orm/models/clinical.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import Any, TYPE_CHECKING

from api.shared.choices.choices import (
    Choices_Sex,
    Choices_Role,
    Choices_AppointmentStatus,
    Choices_ConsultationType,
    Choices_ConsultationStatus,
    Choices_ActivityDirectionTypes,
    Choices_ContactRelationship
)

from api.shared.constants.constants import *

from api.shared.http.mixins import TrimFieldsMixin

# Models located in aapi/infrastructure/orm/models/clinical.py:
# Models: Clinical_Event, Clinical_Event_Image, Consultation, Prescription, Follow_Up, Activity_Log,
# Models: Appointment,


class Clinical_Event(TrimFieldsMixin, models.Model):
    """
    Propósito: Evento clínico unificado: procedimientos, vacunas, acciones.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CLINICAL_EVENTS_RN,
    )
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CLINICAL_EVENTS_RN,
    )
    vet = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.PROTECT,
        related_name=VET_CLINICAL_EVENTS_RN,
        limit_choices_to={"role": Choices_Role.VET},
    )
    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name=CONSULTATION_CLINICAL_EVENTS_RN,
    )
    # --- Estado ---
    is_applied = models.BooleanField(default=False)
    applied_at = models.DateTimeField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(blank=True, null=True)
    # --- Datos principales ---
    occurred_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    procedure_type = models.ForeignKey(
        PROCEDURE_TYPE_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    vaccine_type = models.ForeignKey(
        VACCINE_TYPE_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    # --- Followups / boosters ---
    next_due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    if TYPE_CHECKING:
        id: int
        
    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            # Consultas operativas dentro de una consulta
            models.Index(
                fields=["consultation", "is_applied"],
                name=IDX_CLIONICAL_EVENT_CONSULTATION_APPLIED,
            ),
            models.Index(
                fields=["consultation", "is_closed"],
                name=IDX_CLINICAL_EVENT_CONSULTATION_CLOSED,
            ),

            # Timeline clínico del paciente
            models.Index(
                fields=["pet", "-occurred_at"],
                name=IDX_CLINICAL_EVENT_PET_TIMELINE,
            ),

            # Dashboards / alertas / analytics por centro
            models.Index(
                fields=["veterinary_center", "-occurred_at"],
                name=IDX_CLINICAL_EVENT_CENTER_DATE,
            ),
        ]

        
    @property
    def activity_label(self) -> str:

        if self.procedure_type is not None:
            return self.procedure_type.name

        if self.vaccine_type is not None:
            return self.vaccine_type.name

        raise RuntimeError("Clinical_Event sin procedure_type ni vaccine_type")

    def clean(self):
        super().clean()
        if sum(bool(x) for x in [self.procedure_type, self.vaccine_type]) != 1:
            raise ValidationError("Debe indicar un solo tipo: procedure_type O vaccine_type.")

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        return super().save(*args, **kwargs)


class Clinical_Event_Image(models.Model):
    """
    Propósito: Asocia imágenes a eventos clínicos.

    Entidad de asociación que permite vincular múltiples imágenes a un Clinical_Event,
    preservando metadata clínica como notas y timestamps.

    Invariantes:
    - Un mismo Image no puede asociarse más de una vez al mismo Clinical_Event.
    - Un Clinical_Event puede tener múltiples imágenes distintas.
    """
    clinical_event = models.ForeignKey(
        CLINICAL_EVENT_MODEL,
        on_delete=models.CASCADE,
        related_name=CLINICAL_EVENT_IMAGES_RN,
    )
    image = models.ForeignKey(
        IMAGE_MODEL,
        on_delete=models.CASCADE,
        related_name=IMAGE_CLINICAL_EVENT_IMAGES_RN,
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )
    if TYPE_CHECKING:
        id: int
        clinical_event_id: int
        image_id: int

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["clinical_event", "image"],
                name=UNIQUE_IMAGE_CLINICAL_EVENT_PAIR,
            )
        ]
        indexes = [
            models.Index(
                fields=["clinical_event", "id"],
                name=IDX_CLINICAL_EVENT_IMAGE_EVENT_ID,
            )
        ]

    def __str__(self) -> str:
        return (
            f"ClinicalEventImage("
            f"event_id={self.clinical_event_id}, "
            f"image_id={self.image_id}"
            f")"
        )

class Consultation(TrimFieldsMixin, models.Model):
    """
    Propósito: Acto clínico principal. Punto de unión del dominio clínico.
    """
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CONSULTATIONS_RN,
    )
    brought_by = models.ForeignKey(
        CONTACT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Persona que trajo al paciente a esta consulta"
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CONSULTATIONS_RN
    )
    vet = models.ForeignKey(VET_CENTER_PERSONNEL_MODEL, on_delete=models.PROTECT)
    consultation_type = models.ForeignKey(CONSULTATION_TYPE_MODEL, on_delete=models.PROTECT)

    scheduled_for = models.DateTimeField(null=True, blank=True, 
        help_text="The datetime the consultation was scheduled for")
    consulted_at = models.DateTimeField(
        default=timezone.now,
        help_text="The datetime the consultation was started at, Fecha clínica visible en la historia"
    )
    completed_at = models.DateTimeField(null=True, blank=True, 
        help_text="The datetime the consultation was completed or closed")
    cancelled_at = models.DateTimeField(null=True, blank=True, 
        help_text="The datetime the consultation was cancelled at")
    status = models.CharField(
        max_length=20,
        choices=Choices_ConsultationStatus.choices,
        default=Choices_ConsultationStatus.IN_PROGRESS
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    # SOAP
    subjective = models.TextField(blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    assessment = models.TextField(blank=True, null=True)
    plan = models.TextField(blank=True, null=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        clinical_events: Any
        id: int
        consultation_clinical_events: models.Manager["Clinical_Event"]
        
    def __str__(self):
        return f"Consulta {self.pet.name} — {self.consulted_at:%Y-%m-%d %H:%M}"
    
class Prescription(TrimFieldsMixin, models.Model):
    """
    Propósito: Registro de prescripción médica a un paciente.
    Representa la indicación de un medicamento en un contexto clínico específico.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_PRESCRIPTIONS_RN
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_PRESCRIPTIONS_RN
    )

    medication = models.ForeignKey(
        MEDICATION_MODEL,
        on_delete=models.PROTECT,
        related_name=MEDICATION_PRESCRIPTIONS_RN
    )

    clinical_event = models.ForeignKey(
        CLINICAL_EVENT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CLINICAL_EVENT_PRESCRIPTIONS_RN
    )

    dose = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration_days = models.PositiveIntegerField()

    started_at = models.DateField()

    ended_at = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at", "-id"]

        indexes = [
            models.Index(
                fields=["veterinary_center", "pet"],
                name=IDX_PRESCRIPTION_CENTER_PET
            ),
            models.Index(
                fields=["veterinary_center", "medication"],
                name=IDX_PRESCRIPTION_CENTER_MEDICATION
            ),
            models.Index(
                fields=["clinical_event"],
                name=IDX_PRESCRIPTION_CLINICAL_EVENT
            ),
            models.Index(
                fields=["started_at"],
                name=IDX_PRESCRIPTION_STARTED_AT
            ),
        ]
        
class Follow_Up(TrimFieldsMixin, models.Model):
    """
    Propósito: Seguimiento clínico programado para un paciente.
    Representa una acción futura que debe realizar el centro veterinario.
    Ej: control, llamada, revisión, monitoreo, etc.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_FOLLOW_UPS_RN
    )
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_FOLLOW_UPS_RN
    )
    follow_up_category = models.ForeignKey(
        FOLLOW_UP_CATEGORY_MODEL,
        on_delete=models.PROTECT,
        related_name=CATEGORY_FOLLOW_UPS_RN
    )
    clinical_event = models.ForeignKey(
        CLINICAL_EVENT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CLINICAL_EVENT_FOLLOW_UPS_RN
    )
    contact = models.ForeignKey(
        CONTACT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CONTACT_FOLLOW_UPS_RN
    )
    due_date = models.DateField()
    due_time = models.TimeField(
        null=True,
        blank=True
    )
    done = models.BooleanField(default=False)
    done_at = models.DateTimeField(
        null=True,
        blank=True
    )
    notes = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_date", "due_time", "id"]
        models.UniqueConstraint(
            fields=[
                "veterinary_center",
                "pet",
                "clinical_event",
                "follow_up_category",
                "due_date",
            ],
            name=UNIQUE_FOLLOW_UP_PER_EVENT_CATEGORY_DATE
        )
        indexes = [
            models.Index(
                fields=["veterinary_center", "done", "due_date"],
                name=IDX_FOLLOW_UP_CENTER_DONE_DUE_DATE
            ),
            models.Index(
                fields=["veterinary_center", "pet", "done"],
                name=IDX_FOLLOW_UP_CENTER_PET_DONE
            ),
            models.Index(
                fields=["clinical_event"],
                name=IDX_FOLLOW_UP_CLINICAL_EVENT
            ),
        ]
        
class Activity_Log(TrimFieldsMixin, models.Model):
    """
    Propósito: Bitácora clínica de interacciones con el cliente o relacionadas al paciente.
    Ej: llamadas, mensajes, comunicaciones, acciones administrativas o clínicas.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_ACTIVITY_LOGS_RN
    )
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_ACTIVITY_LOGS_RN
    )
    contact = models.ForeignKey(
        CONTACT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CONTACT_ACTIVITY_LOGS_RN
    )
    vet = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=VET_ACTIVITY_LOGS_RN
    )
    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CONSULTATION_ACTIVITY_LOGS_RN
    )
    follow_up_category = models.ForeignKey(
        FOLLOW_UP_CATEGORY_MODEL,
        on_delete=models.PROTECT,
        related_name=FOLLOW_UP_CATEGORY_ACTIVITY_LOGS_RN
    )
    direction = models.CharField(
        max_length=10,
        choices=Choices_ActivityDirectionTypes.choices
    )
    message = models.TextField()
    outcome = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )
    start_at = models.DateTimeField(
        null=True,
        blank=True
    )
    end_at = models.DateTimeField(
        null=True,
        blank=True
    )
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["veterinary_center", "pet", "created_at"],
                name=IDX_ACTIVITY_LOG_CENTER_PET_CREATED_AT
            ),
            models.Index(
                fields=["veterinary_center", "contact", "created_at"],
                name=IDX_ACTIVITY_LOG_CENTER_CONTACT_CREATED_AT
            ),
            models.Index(
                fields=["consultation"],
                name=IDX_ACTIVITY_LOG_CONSULTATION
            ),
            models.Index(
                fields=["follow_up_category"],
                name=IDX_ACTIVITY_LOG_CATEGORY
            ),
        ]

class Appointment(TrimFieldsMixin, models.Model):
    """
    Propósito: Agenda clínica. Antes de la consulta.
    Snapshot administrativo del paciente y contacto.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_APPOINTMENTS_RN
    )
    assigned_vet = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=ASSIGNED_VET_APPOINTMENTS_RN
    )
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=PET_APPOINTMENTS_RN
    )
    pet_is_registered = models.BooleanField(default=False)
    pet_history_code = models.CharField(
        max_length=40,
        blank=True,
        null=True
    )
    pet_name = models.CharField(max_length=120)
    pet_species = models.CharField(max_length=60)
    pet_breed = models.CharField(
        max_length=80,
        blank=True,
        null=True
    )
    pet_sex = models.CharField(
        max_length=1,
        choices=Choices_Sex.choices,
        default=Choices_Sex.UNDETERMINED
    )
    contact_name = models.CharField(max_length=120)
    contact_dni = models.CharField(max_length=30)
    contact_phone = models.CharField(max_length=30)
    contact_email = models.EmailField(
        blank=True,
        null=True
    )
    relationship_with_pet = models.CharField(
        max_length=20,
        choices=Choices_ContactRelationship.choices
    )
    brought_by_name = models.CharField(max_length=120, blank=True, null=True)
    consultation_type = models.CharField(
        max_length=30,
        choices=Choices_ConsultationType.choices
    )
    consultation_type_other = models.CharField(
        max_length=120,
        blank=True,
        null=True
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Choices_AppointmentStatus.choices,
        default=Choices_AppointmentStatus.SCHEDULED
    )
    reason = models.TextField(
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_start"]
        indexes = [
            models.Index(
                fields=["veterinary_center", "scheduled_start"],
                name=IDX_APPOINTMENT_CENTER_START
            ),
            models.Index(
                fields=["assigned_vet", "scheduled_start"],
                name=IDX_APPOINTMENT_VET_SCHEDULED_START
            ),
            models.Index(
                fields=["pet"],
                name=IDX_APPOINTMENT_PET
            )
        ]

    def clean(self):
        if self.consultation_type != Choices_ConsultationType.OTHER and self.consultation_type_other:
            raise ValidationError(
                "consultation_type_other must be null unless consultation_type is 'other'"
            )
        if self.consultation_type == Choices_ConsultationType.OTHER and not self.consultation_type_other:
            raise ValidationError(
                "consultation_type_other is required when consultation_type is 'other'"
            )
        if not self.pet_is_registered and self.pet:
            raise ValidationError(
                "pet must be null if pet_is_registered is False"
            )
        if self.pet_is_registered and not self.pet:
            raise ValidationError(
                "pet is required if pet_is_registered is True"
            )
        if not self.pet_is_registered and self.pet_history_code:
            raise ValidationError(
                "history_code must be null if pet is not registered"
            )
        if self.scheduled_end <= self.scheduled_start:
            raise ValidationError(
                "scheduled_end must be after scheduled_start"
            )
            
    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pet_name} – {self.scheduled_start:%Y-%m-%d %H:%M}"
    
__all__ = [
    "Clinical_Event", 
    "Clinical_Event_Image", 
    "Consultation", 
    "Prescription", 
    "Follow_Up", 
    "Activity_Log", 
    "Appointment",
]
