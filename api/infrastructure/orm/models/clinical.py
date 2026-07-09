# api/infrastructure/orm/models/clinical.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from api.shared.choices.choices import (
    Choices_Activity_Direction_Types,
    Choices_Appointment_Status,
    Choices_Consultation_Status,
    Choices_Consultation_Type,
    Choices_Contact_Relationship_for_appointments,
    Choices_Role,
    Choices_Sex,
)
from api.shared.constants.constants import (
    CENTER_ACTIVITY_LOGS_RN,
    CENTER_APPOINTMENTS_RN,
    CENTER_CLINICAL_EVENTS_RN,
    CENTER_CONSULTATIONS_RN,
    CENTER_CONTACT_MODEL,
    CENTER_FOLLOW_UPS_RN,
    CENTER_STAFF_MEMBER_MODEL,
    CENTER_PRESCRIPTIONS_RN,
    CLINICAL_EVENT_FOLLOW_UPS_RN,
    CLINICAL_EVENT_IMAGES_RN,
    CLINICAL_EVENT_MODEL,
    CLINICAL_EVENT_PRESCRIPTIONS_RN,
    CONSULTATION_ACTIVITY_LOGS_RN,
    CONSULTATION_CLINICAL_EVENTS_RN,
    CONSULTATION_MODEL,
    CONSULTATION_TYPE_MODEL,
    FOLLOW_UP_CATEGORY_MODEL,
    IDX_ACTIVITY_LOG_CATEGORY,
    IDX_ACTIVITY_LOG_CENTER_CONTACT_CREATED_AT,
    IDX_ACTIVITY_LOG_CENTER_PET_CREATED_AT,
    IDX_ACTIVITY_LOG_CONSULTATION,
    IDX_APPOINTMENT_CENTER_START,
    IDX_APPOINTMENT_PET,
    IDX_APPOINTMENT_VET_SCHEDULED_START,
    IDX_CLINICAL_EVENT_CENTER_DATE,
    IDX_CLINICAL_EVENT_CONSULTATION_APPLIED,
    IDX_CLINICAL_EVENT_CONSULTATION_CLOSED,
    IDX_CLINICAL_EVENT_IMAGE_EVENT_ID,
    IDX_CLINICAL_EVENT_PET_TIMELINE,
    IDX_FOLLOW_UP_CENTER_DONE_DUE_DATE,
    IDX_FOLLOW_UP_CENTER_PET_DONE,
    IDX_FOLLOW_UP_CLINICAL_EVENT,
    IDX_PRESCRIPTION_CENTER_MEDICATION,
    IDX_PRESCRIPTION_CENTER_PET,
    IDX_PRESCRIPTION_CLINICAL_EVENT,
    IDX_PRESCRIPTION_STARTED_AT,
    IMAGE_MODEL,
    MEDICATION_MODEL,
    PET_ACTIVITY_LOGS_RN,
    PET_APPOINTMENTS_RN,
    PET_CLINICAL_EVENTS_RN,
    PET_CONSULTATIONS_RN,
    PET_FOLLOW_UPS_RN,
    PET_MODEL,
    PET_PRESCRIPTIONS_RN,
    PROCEDURE_TYPE_MODEL,
    UNIQUE_FOLLOW_UP_EVENT_CATEGORY_DATE_ACTIVE,
    UNIQUE_FOLLOW_UP_NO_EVENT_CATEGORY_DATE_ACTIVE,
    UNIQUE_IMAGE_CLINICAL_EVENT_PAIR,
    VACCINE_TYPE_MODEL,
    VETERINARY_CENTER_MODEL,
)
from api.shared.orm.audit_mixins import (
    AppliedAuditValidationMixin,
    CancellationAuditValidationMixin,
    ClosedAuditValidationMixin,
    DoneAuditValidationMixin,
    SoftDeleteAuditValidationMixin,
    VoidAuditValidationMixin,
)
from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin


# Models located in api/infrastructure/orm/models/clinical.py:
# Clinical_Event
# Clinical_Event_Image
# Consultation
# Prescription
# Follow_Up
# Activity_Log
# Appointment


def _choice_value(choice: Any) -> str:
    """
    Supports both tuple-style choices and Django TextChoices-style values.
    """
    if isinstance(choice, tuple):
        return str(choice[0])

    return str(choice)


ROLE_VETERINARIAN = _choice_value(Choices_Role.VETERINARIAN)

CONSULTATION_STATUS_IN_PROGRESS = _choice_value(
    Choices_Consultation_Status.IN_PROGRESS
)

APPOINTMENT_STATUS_SCHEDULED = _choice_value(
    Choices_Appointment_Status.SCHEDULED
)

APPOINTMENT_CONSULTATION_TYPE_OTHER = _choice_value(
    Choices_Consultation_Type.OTHER
)

PET_SEX_UNDETERMINED = _choice_value(Choices_Sex.UNDETERMINED)


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


def _get_related_object(
    *,
    instance: models.Model,
    related_field_name: str,
) -> Any | None:
    related_id = getattr(instance, f"{related_field_name}_id", None)

    if related_id is None:
        return None

    try:
        return getattr(instance, related_field_name)
    except Exception:
        return None


def _related_center_id(
    *,
    instance: models.Model,
    related_field_name: str,
) -> int | None:
    related_object = _get_related_object(
        instance=instance,
        related_field_name=related_field_name,
    )

    if related_object is None:
        return None

    return cast(
        int | None,
        getattr(related_object, "veterinary_center_id", None),
    )


def _validate_related_object_belongs_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    related_field_name: str,
    center_field_name: str = "veterinary_center",
) -> None:
    center_id = cast(
        int | None,
        getattr(instance, f"{center_field_name}_id", None),
    )

    if center_id is None:
        return

    related_id = getattr(instance, f"{related_field_name}_id", None)

    if related_id is None:
        return

    found_center_id = _related_center_id(
        instance=instance,
        related_field_name=related_field_name,
    )

    if found_center_id is None:
        return

    if found_center_id != center_id:
        _add_error(
            errors,
            related_field_name,
            (
                f"{related_field_name} must belong to the same veterinary "
                f"center as this record."
            ),
        )


def _validate_audit_actors_belong_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
) -> None:
    for actor_field_name in (
        "created_by",
        "applied_by",
        "closed_by",
        "voided_by",
        "cancelled_by",
        "soft_deleted_by",
        "done_by",
    ):
        if not hasattr(instance, f"{actor_field_name}_id"):
            continue

        _validate_related_object_belongs_to_center(
            instance=instance,
            errors=errors,
            related_field_name=actor_field_name,
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


def _validate_personnel_has_role(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    personnel_field_name: str,
    expected_role: str,
) -> None:
    personnel_id = getattr(instance, f"{personnel_field_name}_id", None)

    if personnel_id is None:
        return

    personnel = _get_related_object(
        instance=instance,
        related_field_name=personnel_field_name,
    )

    if personnel is None:
        return

    role = getattr(personnel, "role", None)

    if role != expected_role:
        _add_error(
            errors,
            personnel_field_name,
            f"{personnel_field_name} must have role {expected_role}.",
        )


def _validate_related_record_belongs_to_same_pet(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    related_field_name: str,
    pet_field_name: str = "pet",
) -> None:
    related_id = getattr(instance, f"{related_field_name}_id", None)
    pet_id = getattr(instance, f"{pet_field_name}_id", None)

    if related_id is None or pet_id is None:
        return

    related_object = _get_related_object(
        instance=instance,
        related_field_name=related_field_name,
    )

    if related_object is None:
        return

    related_pet_id = getattr(related_object, "pet_id", None)

    if related_pet_id is None:
        return

    if int(related_pet_id) != int(pet_id):
        _add_error(
            errors,
            related_field_name,
            f"{related_field_name} must belong to the same pet.",
        )


class Clinical_Event(
    TrimFieldsMixin,
    AppliedAuditValidationMixin,
    ClosedAuditValidationMixin,
    VoidAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Evento clínico unificado: procedimientos, vacunas, acciones.

    Audit/state fields:
    - created_by: who created the record.
    - applied_at / applied_by: when/who applied the event.
    - closed_at / closed_by: when/who closed the event.
    - voided_at / voided_by / void_reason: clinical invalidation.
    - created_at / updated_at: fast timestamps.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CLINICAL_EVENTS_RN,
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CLINICAL_EVENTS_RN,
    )

    vet = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        limit_choices_to={"role": ROLE_VETERINARIAN},
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name=CONSULTATION_CLINICAL_EVENTS_RN,
    )

    is_applied = models.BooleanField(default=False)

    applied_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    applied_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    is_closed = models.BooleanField(default=False)

    closed_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    closed_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    occurred_at = models.DateTimeField(default=timezone.now)

    notes = models.TextField(
        blank=True,
        null=True,
    )

    procedure_type = models.ForeignKey(
        PROCEDURE_TYPE_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
    )

    vaccine_type = models.ForeignKey(
        VACCINE_TYPE_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="+",
    )

    next_due_date = models.DateField(
        blank=True,
        null=True,
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
        default="",
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
        procedure_type_id: int | None
        vaccine_type_id: int | None
        consultation_id: int | None
        pet_id: int
        vet_id: int
        veterinary_center_id: int
        applied_by_id: int | None
        closed_by_id: int | None
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = ["-occurred_at", "-id"]

        indexes = [
            models.Index(
                fields=["consultation", "is_applied"],
                name=IDX_CLINICAL_EVENT_CONSULTATION_APPLIED,
            ),
            models.Index(
                fields=["consultation", "is_closed"],
                name=IDX_CLINICAL_EVENT_CONSULTATION_CLOSED,
            ),
            models.Index(
                fields=["pet", "-occurred_at"],
                name=IDX_CLINICAL_EVENT_PET_TIMELINE,
            ),
            models.Index(
                fields=["veterinary_center", "-occurred_at"],
                name=IDX_CLINICAL_EVENT_CENTER_DATE,
            ),
        ]

    @property
    def activity_label(self) -> str:
        procedure_type = getattr(self, "procedure_type", None)
        vaccine_type = getattr(self, "vaccine_type", None)

        if procedure_type is not None:
            return str(procedure_type.name)

        if vaccine_type is not None:
            return str(vaccine_type.name)

        raise RuntimeError("Clinical_Event sin procedure_type ni vaccine_type")

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        procedure_type_id = cast(
            int | None,
            getattr(self, "procedure_type_id", None),
        )
        vaccine_type_id = cast(
            int | None,
            getattr(self, "vaccine_type_id", None),
        )

        selected_types_count = sum(
            item is not None
            for item in [
                procedure_type_id,
                vaccine_type_id,
            ]
        )

        if selected_types_count != 1:
            _add_error(
                errors,
                "__all__",
                "Debe indicar un solo tipo: procedure_type O vaccine_type.",
            )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="applied_at",
            actor_field="applied_by",
        )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="closed_at",
            actor_field="closed_by",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="vet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="procedure_type",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="vaccine_type",
        )

        _validate_related_record_belongs_to_same_pet(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_personnel_has_role(
            instance=self,
            errors=errors,
            personnel_field_name="vet",
            expected_role=ROLE_VETERINARIAN,
        )

        _raise_errors(errors)


class Clinical_Event_Image(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Asocia imágenes a eventos clínicos.

    Invariantes:
    - Un mismo Image no puede asociarse más de una vez al mismo Clinical_Event activo.
    - Un Clinical_Event puede tener múltiples imágenes distintas.
    - Los vínculos eliminados lógicamente no participan en la unicidad activa.
    """

    clinical_event = models.ForeignKey(
        CLINICAL_EVENT_MODEL,
        on_delete=models.CASCADE,
        related_name=CLINICAL_EVENT_IMAGES_RN,
    )

    image = models.ForeignKey(
        IMAGE_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    notes = models.CharField(
        max_length=255,
        blank=True,
        default="",
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
        clinical_event_id: int
        image_id: int
        soft_deleted_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = ["id"]

        constraints = [
            models.UniqueConstraint(
                fields=["clinical_event", "image"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_IMAGE_CLINICAL_EVENT_PAIR,
            )
        ]

        indexes = [
            models.Index(
                fields=["clinical_event", "id"],
                name=IDX_CLINICAL_EVENT_IMAGE_EVENT_ID,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        clinical_event = _get_related_object(
            instance=self,
            related_field_name="clinical_event",
        )

        image = _get_related_object(
            instance=self,
            related_field_name="image",
        )

        clinical_event_center_id = getattr(
            clinical_event,
            "veterinary_center_id",
            None,
        )

        image_center_id = getattr(
            image,
            "veterinary_center_id",
            None,
        )

        if (
            clinical_event_center_id is not None
            and image_center_id is not None
            and image_center_id != clinical_event_center_id
        ):
            _add_error(
                errors,
                "image",
                "image must belong to the same veterinary center as the clinical event.",
            )

        for actor_field_name in (
            "created_by",
            "soft_deleted_by",
        ):
            actor = _get_related_object(
                instance=self,
                related_field_name=actor_field_name,
            )

            actor_center_id = getattr(actor, "veterinary_center_id", None)

            if (
                clinical_event_center_id is not None
                and actor_center_id is not None
                and actor_center_id != clinical_event_center_id
            ):
                _add_error(
                    errors,
                    actor_field_name,
                    (
                        f"{actor_field_name} must belong to the same "
                        "veterinary center as the clinical event."
                    ),
                )

        _raise_errors(errors)

    def __str__(self) -> str:
        return (
            f"ClinicalEventImage("
            f"event_id={self.clinical_event_id}, "
            f"image_id={self.image_id}"
            f")"
        )


class Consultation(
    TrimFieldsMixin,
    CancellationAuditValidationMixin,
    VoidAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Acto clínico principal. Punto de unión del dominio clínico.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CONSULTATIONS_RN,
    )

    brought_by = models.ForeignKey(
        CENTER_CONTACT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Persona que trajo al paciente a esta consulta",
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CONSULTATIONS_RN,
    )

    vet = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        limit_choices_to={"role": ROLE_VETERINARIAN},
    )

    consultation_type = models.ForeignKey(
        CONSULTATION_TYPE_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The datetime the consultation was scheduled for",
    )

    consulted_at = models.DateTimeField(
        default=timezone.now,
        help_text=(
            "The datetime the consultation was started at, "
            "Fecha clínica visible en la historia"
        ),
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The datetime the consultation was completed or closed",
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The datetime the consultation was cancelled at",
    )

    cancelled_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    cancel_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
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
        default="",
    )

    status = models.CharField(
        max_length=20,
        choices=Choices_Consultation_Status.choices,
        default=CONSULTATION_STATUS_IN_PROGRESS,
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    subjective = models.TextField(
        blank=True,
        null=True,
    )

    objective = models.TextField(
        blank=True,
        null=True,
    )

    assessment = models.TextField(
        blank=True,
        null=True,
    )

    plan = models.TextField(
        blank=True,
        null=True,
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
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
        pet_id: int
        brought_by_id: int | None
        vet_id: int
        veterinary_center_id: int
        consultation_type_id: int
        cancelled_by_id: int | None
        voided_by_id: int | None
        created_by_id: int | None
        clinical_events: Any
        consultation_clinical_events: models.Manager["Clinical_Event"]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="vet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="brought_by",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="consultation_type",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_personnel_has_role(
            instance=self,
            errors=errors,
            personnel_field_name="vet",
            expected_role=ROLE_VETERINARIAN,
        )

        if (
            self.completed_at is not None
            and self.cancelled_at is not None
        ):
            _add_error(
                errors,
                "cancelled_at",
                "A consultation cannot be both completed and cancelled.",
            )

        if (
            self.completed_at is not None
            and self.completed_at < self.consulted_at
        ):
            _add_error(
                errors,
                "completed_at",
                "completed_at cannot be before consulted_at.",
            )

        if (
            self.cancelled_at is not None
            and self.cancelled_at < self.consulted_at
        ):
            _add_error(
                errors,
                "cancelled_at",
                "cancelled_at cannot be before consulted_at.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        pet = cast(Any, getattr(self, "pet", None))
        consulted_at = cast(Any, getattr(self, "consulted_at", None))

        pet_name = getattr(pet, "name", "Paciente")

        if consulted_at is None:
            return f"Consulta {pet_name}"

        return f"Consulta {pet_name} — {consulted_at:%Y-%m-%d %H:%M}"


class Prescription(
    TrimFieldsMixin,
    VoidAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Registro de prescripción médica a un paciente.

    Representa la indicación de un medicamento en un contexto clínico específico.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_PRESCRIPTIONS_RN,
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_PRESCRIPTIONS_RN,
    )

    medication = models.ForeignKey(
        MEDICATION_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    clinical_event = models.ForeignKey(
        CLINICAL_EVENT_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CLINICAL_EVENT_PRESCRIPTIONS_RN,
    )

    dose = models.CharField(max_length=100)

    frequency = models.CharField(max_length=100)

    duration_days = models.PositiveIntegerField()

    started_at = models.DateField()

    ended_at = models.DateField(
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
        default="",
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
        medication_id: int
        clinical_event_id: int | None
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = ["-started_at", "-id"]

        indexes = [
            models.Index(
                fields=["veterinary_center", "pet"],
                name=IDX_PRESCRIPTION_CENTER_PET,
            ),
            models.Index(
                fields=["veterinary_center", "medication"],
                name=IDX_PRESCRIPTION_CENTER_MEDICATION,
            ),
            models.Index(
                fields=["clinical_event"],
                name=IDX_PRESCRIPTION_CLINICAL_EVENT,
            ),
            models.Index(
                fields=["started_at"],
                name=IDX_PRESCRIPTION_STARTED_AT,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="medication",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="clinical_event",
        )

        _validate_related_record_belongs_to_same_pet(
            instance=self,
            errors=errors,
            related_field_name="clinical_event",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        if self.ended_at is not None and self.ended_at < self.started_at:
            _add_error(
                errors,
                "ended_at",
                "ended_at must be on or after started_at.",
            )

        _raise_errors(errors)


class Follow_Up(
    TrimFieldsMixin,
    DoneAuditValidationMixin,
    CancellationAuditValidationMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Seguimiento clínico programado para un paciente.

    Representa una acción futura que debe realizar el centro veterinario.
    Ej: control, llamada, revisión, monitoreo, etc.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_FOLLOW_UPS_RN,
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_FOLLOW_UPS_RN,
    )

    follow_up_category = models.ForeignKey(
        FOLLOW_UP_CATEGORY_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    clinical_event = models.ForeignKey(
        CLINICAL_EVENT_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CLINICAL_EVENT_FOLLOW_UPS_RN,
    )

    contact = models.ForeignKey(
        CENTER_CONTACT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    due_date = models.DateField()

    due_time = models.TimeField(
        null=True,
        blank=True,
    )

    done = models.BooleanField(default=False)

    done_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    done_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    cancel_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
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
        pet_id: int
        follow_up_category_id: int
        clinical_event_id: int | None
        contact_id: int | None
        done_by_id: int | None
        cancelled_by_id: int | None
        soft_deleted_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = ["due_date", "due_time", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "veterinary_center",
                    "pet",
                    "clinical_event",
                    "follow_up_category",
                    "due_date",
                ],
                condition=(
                    models.Q(soft_deleted_at__isnull=True)
                    & models.Q(clinical_event__isnull=False)
                ),
                name=UNIQUE_FOLLOW_UP_EVENT_CATEGORY_DATE_ACTIVE,
            ),
            models.UniqueConstraint(
                fields=[
                    "veterinary_center",
                    "pet",
                    "follow_up_category",
                    "due_date",
                ],
                condition=(
                    models.Q(soft_deleted_at__isnull=True)
                    & models.Q(clinical_event__isnull=True)
                ),
                name=UNIQUE_FOLLOW_UP_NO_EVENT_CATEGORY_DATE_ACTIVE,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "done", "due_date"],
                name=IDX_FOLLOW_UP_CENTER_DONE_DUE_DATE,
            ),
            models.Index(
                fields=["veterinary_center", "pet", "done"],
                name=IDX_FOLLOW_UP_CENTER_PET_DONE,
            ),
            models.Index(
                fields=["clinical_event"],
                name=IDX_FOLLOW_UP_CLINICAL_EVENT,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="follow_up_category",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="clinical_event",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="contact",
        )

        _validate_related_record_belongs_to_same_pet(
            instance=self,
            errors=errors,
            related_field_name="clinical_event",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        if self.done and self.cancelled_at is not None:
            _add_error(
                errors,
                "cancelled_at",
                "A follow-up cannot be both done and cancelled.",
            )

        if self.done and self.soft_deleted_at is not None:
            _add_error(
                errors,
                "soft_deleted_at",
                "A follow-up cannot be both done and deleted.",
            )

        if self.cancelled_at is not None and self.soft_deleted_at is not None:
            _add_error(
                errors,
                "soft_deleted_at",
                "A follow-up cannot be both cancelled and deleted.",
            )

        _raise_errors(errors)


class Activity_Log(
    TrimFieldsMixin,
    VoidAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Bitácora clínica de interacciones con el cliente o relacionadas al paciente.

    Ej:
    - llamadas
    - mensajes
    - comunicaciones
    - acciones administrativas o clínicas

    Importante:
    Este modelo NO reemplaza un audit trail técnico del sistema.
    Esto registra actividades visibles de negocio.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_ACTIVITY_LOGS_RN,
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_ACTIVITY_LOGS_RN,
    )

    contact = models.ForeignKey(
        CENTER_CONTACT_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    vet = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CONSULTATION_ACTIVITY_LOGS_RN,
    )

    follow_up_category = models.ForeignKey(
        FOLLOW_UP_CATEGORY_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
    )

    direction = models.CharField(
        max_length=10,
        choices=Choices_Activity_Direction_Types.choices,
    )

    message = models.TextField()

    outcome = models.CharField(
        max_length=200,
        null=True,
        blank=True,
    )

    start_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    end_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    duration_minutes = models.PositiveIntegerField(
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
        default="",
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
        contact_id: int | None
        vet_id: int | None
        consultation_id: int | None
        follow_up_category_id: int
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = ["-created_at", "-id"]

        indexes = [
            models.Index(
                fields=["veterinary_center", "pet", "created_at"],
                name=IDX_ACTIVITY_LOG_CENTER_PET_CREATED_AT,
            ),
            models.Index(
                fields=["veterinary_center", "contact", "created_at"],
                name=IDX_ACTIVITY_LOG_CENTER_CONTACT_CREATED_AT,
            ),
            models.Index(
                fields=["consultation"],
                name=IDX_ACTIVITY_LOG_CONSULTATION,
            ),
            models.Index(
                fields=["follow_up_category"],
                name=IDX_ACTIVITY_LOG_CATEGORY,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="contact",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="vet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="follow_up_category",
        )

        _validate_related_record_belongs_to_same_pet(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        if (
            self.start_at is not None
            and self.end_at is not None
            and self.end_at < self.start_at
        ):
            _add_error(
                errors,
                "end_at",
                "end_at cannot be before start_at.",
            )

        if (
            self.duration_minutes is not None
            and self.start_at is None
            and self.end_at is None
        ):
            _add_error(
                errors,
                "duration_minutes",
                "duration_minutes requires start_at or end_at.",
            )

        _raise_errors(errors)


class Appointment(
    TrimFieldsMixin,
    CancellationAuditValidationMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Agenda clínica. Antes de la consulta.

    Snapshot administrativo del paciente y contacto.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_APPOINTMENTS_RN,
    )

    assigned_vet = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        limit_choices_to={"role": ROLE_VETERINARIAN},
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=PET_APPOINTMENTS_RN,
    )

    pet_is_registered = models.BooleanField(default=False)

    pet_history_code = models.CharField(
        max_length=40,
        blank=True,
        null=True,
    )

    pet_name = models.CharField(max_length=120)

    pet_species = models.CharField(max_length=60)

    pet_breed = models.CharField(
        max_length=80,
        blank=True,
        null=True,
    )

    pet_sex = models.CharField(
        max_length=1,
        choices=Choices_Sex.choices,
        default=PET_SEX_UNDETERMINED,
    )

    contact_name = models.CharField(max_length=120)

    contact_document_id = models.CharField(max_length=30)

    contact_phone = models.CharField(max_length=30)

    contact_email = models.EmailField(
        blank=True,
        null=True,
    )

    relationship_with_pet = models.CharField(
        max_length=20,
        choices=Choices_Contact_Relationship_for_appointments.choices,
    )

    brought_by_name = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    consultation_type = models.CharField(
        max_length=30,
        choices=Choices_Consultation_Type.choices,
    )

    consultation_type_other = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    scheduled_start = models.DateTimeField()

    scheduled_end = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=Choices_Appointment_Status.choices,
        default=APPOINTMENT_STATUS_SCHEDULED,
    )

    reason = models.TextField(
        blank=True,
        null=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    cancel_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
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
        pet_id: int | None
        assigned_vet_id: int | None
        veterinary_center_id: int
        cancelled_by_id: int | None
        soft_deleted_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = ["scheduled_start"]

        indexes = [
            models.Index(
                fields=["veterinary_center", "scheduled_start"],
                name=IDX_APPOINTMENT_CENTER_START,
            ),
            models.Index(
                fields=["assigned_vet", "scheduled_start"],
                name=IDX_APPOINTMENT_VET_SCHEDULED_START,
            ),
            models.Index(
                fields=["pet"],
                name=IDX_APPOINTMENT_PET,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        consultation_type = cast(
            str | None,
            getattr(self, "consultation_type", None),
        )
        consultation_type_other = cast(
            str | None,
            getattr(self, "consultation_type_other", None),
        )
        pet_is_registered = cast(
            bool,
            getattr(self, "pet_is_registered", False),
        )
        pet_id = cast(
            int | None,
            getattr(self, "pet_id", None),
        )
        pet_history_code = cast(
            str | None,
            getattr(self, "pet_history_code", None),
        )
        scheduled_start = getattr(self, "scheduled_start", None)
        scheduled_end = getattr(self, "scheduled_end", None)

        if (
            consultation_type != APPOINTMENT_CONSULTATION_TYPE_OTHER
            and consultation_type_other
        ):
            _add_error(
                errors,
                "consultation_type_other",
                (
                    "consultation_type_other must be null unless "
                    "consultation_type is 'other'."
                ),
            )

        if (
            consultation_type == APPOINTMENT_CONSULTATION_TYPE_OTHER
            and not consultation_type_other
        ):
            _add_error(
                errors,
                "consultation_type_other",
                (
                    "consultation_type_other is required when "
                    "consultation_type is 'other'."
                ),
            )

        if not pet_is_registered and pet_id:
            _add_error(
                errors,
                "pet",
                "pet must be null if pet_is_registered is False.",
            )

        if pet_is_registered and not pet_id:
            _add_error(
                errors,
                "pet",
                "pet is required if pet_is_registered is True.",
            )

        if not pet_is_registered and pet_history_code:
            _add_error(
                errors,
                "pet_history_code",
                "history_code must be null if pet is not registered.",
            )

        if (
            scheduled_start is not None
            and scheduled_end is not None
            and scheduled_end <= scheduled_start
        ):
            _add_error(
                errors,
                "scheduled_end",
                "scheduled_end must be after scheduled_start.",
            )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="assigned_vet",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_personnel_has_role(
            instance=self,
            errors=errors,
            personnel_field_name="assigned_vet",
            expected_role=ROLE_VETERINARIAN,
        )

        if self.cancelled_at is not None and self.soft_deleted_at is not None:
            _add_error(
                errors,
                "soft_deleted_at",
                "An appointment cannot be both cancelled and deleted.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        pet_name = cast(str, getattr(self, "pet_name", ""))
        scheduled_start = getattr(self, "scheduled_start", None)

        if scheduled_start is None:
            return pet_name

        return f"{pet_name} – {scheduled_start:%Y-%m-%d %H:%M}"


__all__ = [
    "Clinical_Event",
    "Clinical_Event_Image",
    "Consultation",
    "Prescription",
    "Follow_Up",
    "Activity_Log",
    "Appointment",
]