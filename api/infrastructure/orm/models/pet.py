# api/infrastructure/orm/models/pet.py

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, cast

from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.utils import timezone

from api.domains.pet.contact_link_policy import validate_pet_contact_link_consistency
from api.domains.pet.errors import PetContactLinkBillingResponsibleRequiresBillingPermissionError, PetContactLinkCenterContactDifferentCenterError, PetContactLinkInvalidRoleForInstitutionError, PetContactLinkInvalidRoleForPersonError, PetRuleViolationError

from api.shared.choices.choices import (
    Choices_Critical_Case_Status,
    Choices_Disease_Case_Status,
    Choices_Disease_Event_Type,
    Choices_Pet_Clinical_Record_Status,
    Choices_Pet_Contact_Link_Role,
    Choices_Pet_Status,
    Choices_Problem_Case_Status,
    Choices_Problem_Event_Type,
    Choices_Severity_Level,
    Choices_Sex,
    Choices_Size,
)
from api.shared.constants.constants import (
    BREED_IN_CENTER_MODEL,
    CENTER_CONTACT_MODEL,
    CENTER_CONTACT_PET_CONTACT_LINKS_RN,
    CENTER_CRITICAL_CASES_RN,
    CENTER_DISEASE_CASES_RN,
    CENTER_DISEASE_EVENTS_RN,
    CENTER_STAFF_MEMBERSHIP_MODEL,
    CENTER_PROBLEM_CASES_RN,
    CENTER_PROBLEM_EVENTS_RN,
    CONSULTATION_CRITICAL_CASES_RN,
    CONSULTATION_DISEASE_EVENTS_RN,
    CONSULTATION_MODEL,
    CONSULTATION_PROBLEM_EVENTS_RN,
    CREATED_BY_CRITICAL_CASES_RN,
    CREATED_BY_DISEASE_CASES_RN,
    CREATED_BY_PROBLEM_CASES_RN,
    CRITICAL_CASE_SINGLE_ORIGIN,
    DISEASE_CASES_CLINICAL_COMORBIDITIES_RN,
    DISEASE_CASE_CRITICAL_CASES_RN,
    DISEASE_CASE_EVENTS_RN,
    DISEASE_CATALOG_CASES_RN,
    DISEASE_CATALOG_MODEL,
    IDX_CRITICAL_CENTER_STATUS,
    IDX_CRITICAL_PET_STATUS,
    IDX_CRITICAL_STATUS,
    IDX_DISEASE_EVENT_CASE_TIMELINE,
    IDX_DISEASE_EVENT_CASE_TYPE,
    IDX_DISEASE_EVENT_CENTER_TIMELINE,
    IDX_DISEASE_EVENT_CONSULTATION,
    IDX_DISEASE_EVENT_TYPE,
    IDX_PROBLEM_CASE_CATALOG,
    IDX_PROBLEM_CASE_CENTER_PET,
    IDX_PROBLEM_CASE_PET_FIRST_NOTED,
    IDX_PROBLEM_CASE_PET_STATUS,
    IDX_PROBLEM_CASE_RELAPSE,
    IDX_PROBLEM_EVENT_CASE_DATE_ID,
    IDX_PROBLEM_EVENT_CENTER_DATE,
    INITIAL_CONSULTATION_DISEASE_CASES_RN,
    LAST_ATTENDING_VET_PETS_RN,
    MERGED_BY_PETS_RN,
    MERGED_PET_PETS_RN,
    PET_CLINICAL_COMORBIDITIES_RN,
    PET_CRITICAL_CASES_RN,
    PET_DISEASE_CASES_RN,
    PET_DISEASE_CASE_MODEL,
    PET_MODEL,
    PET_PET_CONTACT_LINKS_RN,
    PET_PROBLEM_CASES_RN,
    PET_PROBLEM_CASE_MODEL,
    PROBLEM_CASE_CRITICAL_CASES_RN,
    PROBLEM_CASE_PROBLEM_EVENTS_RN,
    PROBLEM_CATALOG_MODEL,
    PROBLEM_CATALOG_PROBLEM_CASES_RN,
    RELAPSED_DISEASE_CASES_RN,
    RELAPSED_PROBLEM_CASES_RN,
    RESOLVED_BY_DISEASE_CASES_RN,
    SELF,
    SPECIES_IN_CENTER_MODEL,
    SPECIES_PETS_RN,
    UNIQUE_ACTIVE_CRITICAL_CASE_PER_CONSULTATION,
    UNIQUE_ACTIVE_CRITICAL_CASE_PER_DISEASE_CASE,
    UNIQUE_ACTIVE_CRITICAL_CASE_PER_PROBLEM_CASE,
    UNIQUE_COMORBIDITY_PER_PET,
    UNIQUE_DISEASE_EVENT_PER_CASE_TYPE_DATETIME_CONSULTATION,
    UNIQUE_HISTORY_PET_CENTER,
    UNIQUE_PROBLEM_CASE_PER_PET_PROBLEM_DATE_PER_CENTER,
    UNIQUE_PROBLEM_EVENT_PER_CASE_TYPE_DATE,
    VETERINARY_CENTER_MODEL,
)
from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin
from api.shared.utils.microchip_validator import microchip_validator


# Models in api/infrastructure/orm/models/pet.py:
# - Pet_History_Sequence
# - Pet_Contact_Link
# - Pet
# - Pet_Disease_Case
# - Pet_Problem_Case
# - Pet_Disease_Event
# - Clinical_Comorbidity
# - Pet_Problem_Event
# - Critical_Case


if TYPE_CHECKING:
    from .clinical import Consultation


def _choice_value(choice: Any) -> str:
    """
    Supports both tuple-style choices and Django TextChoices-style values.
    """
    if isinstance(choice, tuple):
        return str(choice[0])

    return str(choice)


PET_STATUS_ACTIVE = _choice_value(Choices_Pet_Status.ACTIVE)
PET_STATUS_INACTIVE = _choice_value(Choices_Pet_Status.INACTIVE)
PET_STATUS_DECEASED = _choice_value(Choices_Pet_Status.DECEASED)
PET_STATUS_ARCHIVED = _choice_value(Choices_Pet_Status.ARCHIVED)

PET_CLINICAL_RECORD_STATUS_DRAFT = _choice_value(
    Choices_Pet_Clinical_Record_Status.DRAFT
)

DISEASE_CASE_STATUS_ACTIVE = _choice_value(Choices_Disease_Case_Status.ACTIVE)
DISEASE_CASE_STATUS_RESOLVED = _choice_value(
    Choices_Disease_Case_Status.RESOLVED
)

PROBLEM_CASE_STATUS_ACTIVE = _choice_value(Choices_Problem_Case_Status.ACTIVE)
PROBLEM_CASE_STATUS_INACTIVE = _choice_value(
    Choices_Problem_Case_Status.INACTIVE
)
PROBLEM_CASE_STATUS_RESOLVED = _choice_value(
    Choices_Problem_Case_Status.RESOLVED
)

CRITICAL_CASE_STATUS_ACTIVE = _choice_value(Choices_Critical_Case_Status.ACTIVE)
CRITICAL_CASE_STATUS_RESOLVED = _choice_value(
    Choices_Critical_Case_Status.RESOLVED
)


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


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _nullable_clean(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()

    return cleaned_value or None


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


def _related_pet_id(
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
        getattr(related_object, "pet_id", None),
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

    if int(found_center_id) != int(center_id):
        _add_error(
            errors,
            related_field_name,
            (
                f"{related_field_name} must belong to the same veterinary "
                "center as this record."
            ),
        )


def _validate_related_object_belongs_to_pet(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    related_field_name: str,
    pet_field_name: str = "pet",
) -> None:
    pet_id = cast(
        int | None,
        getattr(instance, f"{pet_field_name}_id", None),
    )

    if pet_id is None:
        return

    related_id = getattr(instance, f"{related_field_name}_id", None)

    if related_id is None:
        return

    found_pet_id = _related_pet_id(
        instance=instance,
        related_field_name=related_field_name,
    )

    if found_pet_id is None:
        return

    if int(found_pet_id) != int(pet_id):
        _add_error(
            errors,
            related_field_name,
            f"{related_field_name} must belong to the same pet.",
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
        "resolved_by",
        "voided_by",
        "soft_deleted_by",
        "merged_by",
        "last_attending_vet",
    ):
        if not hasattr(instance, f"{actor_field_name}_id"):
            continue

        _validate_related_object_belongs_to_center(
            instance=instance,
            errors=errors,
            related_field_name=actor_field_name,
        )


def _validate_consultation_belongs_to_case_pet(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
    consultation_field_name: str,
    case_field_name: str,
) -> None:
    consultation = _get_related_object(
        instance=instance,
        related_field_name=consultation_field_name,
    )

    case = _get_related_object(
        instance=instance,
        related_field_name=case_field_name,
    )

    if consultation is None or case is None:
        return

    consultation_pet_id = getattr(consultation, "pet_id", None)
    case_pet_id = getattr(case, "pet_id", None)

    if consultation_pet_id is None or case_pet_id is None:
        return

    if int(consultation_pet_id) != int(case_pet_id):
        _add_error(
            errors,
            consultation_field_name,
            f"{consultation_field_name} must belong to the same pet as the case.",
        )


class Pet_History_Sequence(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Secuencia anual por centro para generar history_code de pacientes.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
    )

    year = models.IntegerField()

    last_value = models.IntegerField(
        default=0,
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "year"],
                name="uniq_pet_history_seq_center_year",
            )
        ]

    def __str__(self) -> str:
        return f"{self.veterinary_center} - {self.year} - {self.last_value}"


class Pet_Contact_Link(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Relación entre una mascota y un contacto de centro.

    Aquí vive el rol del contacto para esta mascota y también los permisos
    reales que tiene ese contacto dentro de esta relación.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_PET_CONTACT_LINKS_RN,
    )

    center_contact = models.ForeignKey(
        CENTER_CONTACT_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CONTACT_PET_CONTACT_LINKS_RN,
    )

    role = models.CharField(
        max_length=40,
        choices=Choices_Pet_Contact_Link_Role.choices,
        db_index=True,
    )

    is_primary_contact = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si este es el contacto principal del paciente.",
    )

    specific_relationship = models.CharField(
        max_length=80,
        blank=True,
        help_text=(
            "Texto libre: madre, padre, vecino, fundación, paseador, "
            "clínica remitente, etc."
        ),
    )

    can_authorize_treatment = models.BooleanField(
        default=False,
        help_text="Puede autorizar tratamientos, procedimientos o decisiones clínicas.",
    )

    can_receive_medical_updates = models.BooleanField(
        default=False,
        help_text="Puede recibir información médica de la mascota.",
    )

    can_receive_billing = models.BooleanField(
        default=False,
        help_text="Puede recibir facturas, presupuestos o información de pago.",
    )

    can_pickup_pet = models.BooleanField(
        default=False,
        help_text="Puede retirar o recibir la mascota.",
    )

    is_emergency_contact = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si este contacto puede usarse como contacto de emergencia.",
    )

    notes = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    soft_deleted_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        center_contact_id: int
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        verbose_name = "Relación contacto-mascota"
        verbose_name_plural = "Relaciones contacto-mascota"

        indexes = [
            models.Index(fields=["pet", "role"]),
            models.Index(fields=["center_contact", "role"]),
            models.Index(fields=["pet", "is_primary_contact"]),
            models.Index(fields=["pet", "is_active"]),
            models.Index(fields=["pet", "soft_deleted_at"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["pet", "center_contact", "role"],
                condition=Q(
                    is_active=True,
                    soft_deleted_at__isnull=True,
                ),
                name="unique_active_center_contact_role_per_pet",
            ),
            models.UniqueConstraint(
                fields=["pet"],
                condition=Q(
                    is_primary_contact=True,
                    is_active=True,
                    soft_deleted_at__isnull=True,
                ),
                name="unique_primary_contact_per_pet",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.specific_relationship = _clean_string(self.specific_relationship)
        self.notes = _clean_string(self.notes)

        if self.soft_deleted_at is not None:
            self.is_active = False

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

        pet = _get_related_object(
            instance=self,
            related_field_name="pet",
        )

        pet_center_id = getattr(pet, "veterinary_center_id", None)

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
                pet_center_id is not None
                and actor_center_id is not None
                and int(actor_center_id) != int(pet_center_id)
            ):
                _add_error(
                    errors,
                    actor_field_name,
                    (
                        f"{actor_field_name} must belong to the same "
                        "veterinary center as the pet."
                    ),
                )

        _raise_errors(errors)

        if not self.pet_id or not self.center_contact_id:
            return

        try:
            validate_pet_contact_link_consistency(
                pet_center_id=self.pet.veterinary_center_id,
                center_contact_center_id=(
                    self.center_contact.veterinary_center_id
                ),
                center_contact_type=self.center_contact.center_contact_type,
                role=self.role,
                is_active=self.is_active,
                can_receive_billing=self.can_receive_billing,
            )

        except PetContactLinkCenterContactDifferentCenterError as exc:
            raise ValidationError(
                {
                    "center_contact": str(exc),
                }
            ) from exc

        except (
            PetContactLinkInvalidRoleForPersonError,
            PetContactLinkInvalidRoleForInstitutionError,
        ) as exc:
            raise ValidationError(
                {
                    "role": str(exc),
                }
            ) from exc

        except PetContactLinkBillingResponsibleRequiresBillingPermissionError as exc:
            raise ValidationError(
                {
                    "can_receive_billing": str(exc),
                }
            ) from exc

        except PetRuleViolationError as exc:
            raise ValidationError(str(exc)) from exc

    def __str__(self) -> str:
        pet_name = getattr(self.pet, "name", str(self.pet))
        contact_name = getattr(
            self.center_contact,
            "display_name",
            str(self.center_contact),
        )

        try:
            role_label = Choices_Pet_Contact_Link_Role(self.role).label
        except ValueError:
            role_label = self.role

        return f"{pet_name} — {contact_name} ({role_label})"


class Pet(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Paciente veterinario. Núcleo clínico del sistema.

    Contact model rule:
    Pet does not link directly to Center_Contact.
    Pet links to Pet_Contact_Link through the reverse relation
    `pet_pet_contact_links`, and Pet_Contact_Link links to Center_Contact.
    """

    history_code = models.CharField(
        max_length=50,
        db_index=True,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        db_index=True,
    )

    sex = models.CharField(
        max_length=1,
        choices=Choices_Sex.choices,
    )

    species = models.ForeignKey(
        SPECIES_IN_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=SPECIES_PETS_RN,
    )

    breed = models.ForeignKey(
        BREED_IN_CENTER_MODEL,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    sterilized = models.BooleanField(
        default=False,
    )

    birth_date = models.DateField(
        blank=True,
        null=True,
    )

    body_description = models.CharField(
        max_length=300,
        blank=True,
        null=True,
    )

    size = models.CharField(
        max_length=20,
        choices=Choices_Size.choices,
        blank=True,
        null=True,
    )

    last_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        blank=True,
        null=True,
    )

    last_attending_vet = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=LAST_ATTENDING_VET_PETS_RN,
    )

    last_attending_vet_external_name = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    has_pedigree = models.BooleanField(
        default=False,
    )

    pedigree_registry = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    has_visual_identification = models.BooleanField(
        default=False,
    )

    visual_tag = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Placa",
    )

    visual_identification_or_tattoo_description = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    has_microchip = models.BooleanField(
        default=False,
    )

    microchip_code = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        validators=[microchip_validator],
        db_index=True,
    )

    microchip_date = models.DateField(
        blank=True,
        null=True,
    )

    microchip_body_region = models.CharField(
        max_length=80,
        blank=True,
        null=True,
    )

    clinical_observations = models.TextField(
        max_length=150,
        blank=True,
        null=True,
    )

    internal_notes = models.TextField(
        max_length=100,
        blank=True,
        null=True,
    )

    photo_url = models.URLField(
        blank=True,
        null=True,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
    )

    status = models.CharField(
        max_length=16,
        choices=Choices_Pet_Status.choices,
        default=PET_STATUS_ACTIVE,
        db_index=True,
    )

    inactive_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the patient was marked as inactive",
    )

    deceased_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the patient was declared deceased",
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the patient was archived read-only",
    )

    clinical_record_status = models.CharField(
        max_length=20,
        choices=Choices_Pet_Clinical_Record_Status.choices,
        default=PET_CLINICAL_RECORD_STATUS_DRAFT,
        db_index=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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

    master_pet = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=MERGED_PET_PETS_RN,
        help_text="If this pet was merged into another patient",
    )

    merged_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    merged_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=MERGED_BY_PETS_RN,
    )

    if TYPE_CHECKING:
        id: int
        species_id: int
        breed_id: int | None
        veterinary_center_id: int
        last_attending_vet_id: int | None
        created_by_id: int | None
        master_pet_id: int | None
        merged_by_id: int | None

        pet_pet_contact_links: models.Manager["Pet_Contact_Link"]
        pet_disease_cases: models.Manager["Pet_Disease_Case"]
        pet_problem_cases: models.Manager["Pet_Problem_Case"]
        pet_consultations: models.Manager["Consultation"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "history_code"],
                name=UNIQUE_HISTORY_PET_CENTER,
            ),
            models.UniqueConstraint(
                fields=["microchip_code"],
                condition=Q(microchip_code__isnull=False),
                name="uniq_pet_microchip_code_global",
            ),
        ]

        indexes = [
            models.Index(fields=["veterinary_center", "history_code"]),
            models.Index(fields=["veterinary_center", "name"]),
            models.Index(fields=["veterinary_center", "status"]),
            models.Index(fields=["veterinary_center", "species", "breed"]),
            models.Index(fields=["veterinary_center", "microchip_code"]),
        ]

    @property
    def active_pet_contact_links(self):
        return self.pet_pet_contact_links.select_related("center_contact").filter(
            is_active=True,
            soft_deleted_at__isnull=True,
        )

    @property
    def owner_guardians(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.OWNER_GUARDIAN.value,
        )

    @property
    def caregivers(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.CAREGIVER.value,
        )

    @property
    def billing_responsibles(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.BILLING_RESPONSIBLE.value,
        )

    @property
    def emergency_contacts(self):
        return self.active_pet_contact_links.filter(
            is_emergency_contact=True,
        )

    @property
    def pickup_authorized_contacts(self):
        return self.active_pet_contact_links.filter(
            can_pickup_pet=True,
        )

    @property
    def treatment_authorization_contacts(self):
        return self.active_pet_contact_links.filter(
            can_authorize_treatment=True,
        )

    @property
    def medical_update_contacts(self):
        return self.active_pet_contact_links.filter(
            can_receive_medical_updates=True,
        )

    @property
    def billing_update_contacts(self):
        return self.active_pet_contact_links.filter(
            can_receive_billing=True,
        )

    @property
    def referring_vets(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.REFERRING_VET.value,
        )

    @property
    def responsible_institutions(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.RESPONSIBLE_INSTITUTION.value,
        )

    @property
    def referring_institutions(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.REFERRING_INSTITUTION.value,
        )

    @property
    def breeders(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.BREEDER.value,
        )

    @property
    def shelters_or_foundations(self):
        return self.active_pet_contact_links.filter(
            role=Choices_Pet_Contact_Link_Role.SHELTER_OR_FOUNDATION.value,
        )

    @property
    def primary_pet_contact_link(self):
        return self.active_pet_contact_links.filter(
            is_primary_contact=True,
        ).first()

    @property
    def primary_center_contact(self):
        pet_contact_link = self.primary_pet_contact_link

        return pet_contact_link.center_contact if pet_contact_link else None

    @property
    def primary_owner_guardian(self):
        pet_contact_link = self.owner_guardians.filter(
            is_primary_contact=True,
        ).first()

        return pet_contact_link.center_contact if pet_contact_link else None

    @property
    def master(self) -> "Pet":
        pet: "Pet" = self
        visited: set[int] = set()

        while pet.master_pet_id is not None:
            if pet.pk is not None:
                if pet.pk in visited:
                    break

                visited.add(pet.pk)

            pet = pet.master_pet  # type: ignore[assignment]

        return pet

    @property
    def is_master(self) -> bool:
        return self.master_pet_id is None

    @property
    def is_merged(self) -> bool:
        return self.master_pet_id is not None

    @property
    def age(self) -> int | None:
        if not self.birth_date:
            return None

        today = date.today()

        return (
            today.year
            - self.birth_date.year
            - (
                (today.month, today.day)
                < (self.birth_date.month, self.birth_date.day)
            )
        )

    @property
    def is_editable(self) -> bool:
        return self.clinical_record_status == PET_CLINICAL_RECORD_STATUS_DRAFT

    def normalize_nullable_text_fields(self) -> None:
        self.name = _clean_string(self.name)
        self.reference = _clean_string(self.reference)
        self.body_description = _nullable_clean(self.body_description)
        self.size = _nullable_clean(self.size)
        self.pedigree_registry = _nullable_clean(self.pedigree_registry)
        self.visual_tag = _nullable_clean(self.visual_tag)
        self.visual_identification_or_tattoo_description = _nullable_clean(
            self.visual_identification_or_tattoo_description,
        )
        self.microchip_code = _nullable_clean(self.microchip_code)
        self.microchip_body_region = _nullable_clean(self.microchip_body_region)
        self.clinical_observations = _nullable_clean(self.clinical_observations)
        self.internal_notes = _nullable_clean(self.internal_notes)
        self.photo_url = _nullable_clean(self.photo_url)

    def assign_history_code_if_missing(self) -> None:
        """
        Explicit creation step.

        Must be called by the command/service before:
        - pet.full_clean()
        - pet.save()

        Do not hide this in save().
        """

        if self.pk is not None or self.history_code:
            return

        if not self.veterinary_center_id:
            raise ValidationError(
                {
                    "veterinary_center": (
                        "veterinary_center is required before generating history_code."
                    )
                }
            )

        with transaction.atomic():
            year = timezone.now().year

            try:
                seq, _ = Pet_History_Sequence.objects.select_for_update().get_or_create(
                    veterinary_center_id=self.veterinary_center_id,
                    year=year,
                    defaults={"last_value": 0},
                )

            except IntegrityError:
                seq = Pet_History_Sequence.objects.select_for_update().get(
                    veterinary_center_id=self.veterinary_center_id,
                    year=year,
                )

            seq.last_value += 1
            seq.full_clean()
            seq.save(update_fields=["last_value"])

            center = self.veterinary_center

            self.history_code = (
                f"{center.country_code}-"
                f"{center.clinic_code}-"
                f"{year}-"
                f"{seq.last_value:05d}"
            )

    def _validate_master_pet_cycle(
        self,
        *,
        errors: dict[str, list[str]],
    ) -> None:
        if self.master_pet_id is None:
            return

        if self.pk is not None and self.master_pet_id == self.pk:
            _add_error(
                errors,
                "master_pet",
                "A pet cannot be merged into itself.",
            )
            return

        visited: set[int] = set()

        master_pet = _get_related_object(
            instance=self,
            related_field_name="master_pet",
        )

        while master_pet is not None:
            master_pet_id = getattr(master_pet, "id", None)
            next_master_pet_id = getattr(master_pet, "master_pet_id", None)

            if master_pet_id is None:
                break

            if self.pk is not None and int(master_pet_id) == int(self.pk):
                _add_error(
                    errors,
                    "master_pet",
                    "Pet merge chain cannot contain a cycle.",
                )
                return

            if int(master_pet_id) in visited:
                _add_error(
                    errors,
                    "master_pet",
                    "Pet merge chain cannot contain a cycle.",
                )
                return

            visited.add(int(master_pet_id))

            if next_master_pet_id is None:
                break

            master_pet = getattr(master_pet, "master_pet", None)

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.normalize_nullable_text_fields()

        if not self.name:
            _add_error(
                errors,
                "name",
                "Pet name is required.",
            )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="species",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="last_attending_vet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="created_by",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="merged_by",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="master_pet",
        )

        if self.breed_id and self.species_id:
            breed = _get_related_object(
                instance=self,
                related_field_name="breed",
            )

            breed_species_in_center_id = getattr(
                breed,
                "species_in_center_id",
                None,
            )

            if (
                breed_species_in_center_id is not None
                and int(breed_species_in_center_id) != int(self.species_id)
            ):
                _add_error(
                    errors,
                    "breed",
                    "Breed must belong to the selected species in center.",
                )

        if self.has_microchip:
            if not self.microchip_code:
                _add_error(
                    errors,
                    "microchip_code",
                    "microchip_code is required when has_microchip is True.",
                )
        else:
            self.microchip_code = None
            self.microchip_date = None
            self.microchip_body_region = None

        if self.has_visual_identification:
            if (
                not self.visual_tag
                and not self.visual_identification_or_tattoo_description
            ):
                _add_error(
                    errors,
                    "visual_identification_or_tattoo_description",
                    (
                        "Visual tag or visual/tattoo description is required "
                        "when has_visual_identification is True."
                    ),
                )
        else:
            self.visual_tag = None
            self.visual_identification_or_tattoo_description = None

        if not self.has_pedigree:
            self.pedigree_registry = None

        if self.status == PET_STATUS_ACTIVE:
            if self.inactive_at is not None:
                _add_error(
                    errors,
                    "inactive_at",
                    "inactive_at must be null while pet status is ACTIVE.",
                )

            if self.deceased_at is not None:
                _add_error(
                    errors,
                    "deceased_at",
                    "deceased_at must be null while pet status is ACTIVE.",
                )

            if self.archived_at is not None:
                _add_error(
                    errors,
                    "archived_at",
                    "archived_at must be null while pet status is ACTIVE.",
                )

        if self.status == PET_STATUS_INACTIVE:
            if self.inactive_at is None:
                _add_error(
                    errors,
                    "inactive_at",
                    "inactive_at is required when pet status is INACTIVE.",
                )

            if self.deceased_at is not None:
                _add_error(
                    errors,
                    "deceased_at",
                    "deceased_at must be null when pet status is INACTIVE.",
                )

            if self.archived_at is not None:
                _add_error(
                    errors,
                    "archived_at",
                    "archived_at must be null when pet status is INACTIVE.",
                )

        if self.status == PET_STATUS_DECEASED:
            if self.deceased_at is None:
                _add_error(
                    errors,
                    "deceased_at",
                    "deceased_at is required when pet status is DECEASED.",
                )

            if self.inactive_at is not None:
                _add_error(
                    errors,
                    "inactive_at",
                    "inactive_at must be null when pet status is DECEASED.",
                )

            if self.archived_at is not None:
                _add_error(
                    errors,
                    "archived_at",
                    "archived_at must be null when pet status is DECEASED.",
                )

        if self.status == PET_STATUS_ARCHIVED:
            if self.archived_at is None:
                _add_error(
                    errors,
                    "archived_at",
                    "archived_at is required when pet status is ARCHIVED.",
                )

            if self.inactive_at is not None:
                _add_error(
                    errors,
                    "inactive_at",
                    "inactive_at must be null when pet status is ARCHIVED.",
                )

            if self.deceased_at is not None:
                _add_error(
                    errors,
                    "deceased_at",
                    "deceased_at must be null when pet status is ARCHIVED.",
                )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="merged_at",
            actor_field="merged_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="merged_at",
            actor_field="merged_by",
        )

        if self.master_pet_id is not None and self.merged_at is None:
            _add_error(
                errors,
                "merged_at",
                "merged_at is required when master_pet is set.",
            )

        if self.master_pet_id is None and self.merged_at is not None:
            _add_error(
                errors,
                "master_pet",
                "master_pet is required when merged_at is set.",
            )

        self._validate_master_pet_cycle(errors=errors)

        _raise_errors(errors)

    def __str__(self) -> str:
        species_name = getattr(self.species, "name", "")

        if not species_name:
            global_species = getattr(self.species, "global_species", None)
            species_name = getattr(global_species, "name", "")

        return f"{self.name} ({species_name})"


class Pet_Disease_Case(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Un caso clínico de enfermedad en un paciente.
    Vive en el tiempo.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_DISEASE_CASES_RN,
    )

    disease_catalog = models.ForeignKey(
        DISEASE_CATALOG_MODEL,
        on_delete=models.PROTECT,
        related_name=DISEASE_CATALOG_CASES_RN,
    )

    relapsed_from_case = models.ForeignKey(
        SELF,
        null=True,
        blank=True,
        related_name=RELAPSED_DISEASE_CASES_RN,
        on_delete=models.PROTECT,
    )

    diagnosis_date = models.DateField(
        default=timezone.localdate,
    )

    initial_consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=INITIAL_CONSULTATION_DISEASE_CASES_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_DISEASE_CASES_RN,
    )

    status = models.CharField(
        max_length=20,
        choices=Choices_Disease_Case_Status.choices,
        default=DISEASE_CASE_STATUS_ACTIVE,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=RESOLVED_BY_DISEASE_CASES_RN,
    )

    is_chronic = models.BooleanField(
        default=False,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        CENTER_STAFF_MEMBERSHIP_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CREATED_BY_DISEASE_CASES_RN,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        disease_case_events: Any
        id: int
        pet_id: int
        disease_catalog_id: int
        veterinary_center_id: int
        relapsed_from_case_id: int | None
        initial_consultation_id: int | None
        resolved_by_id: int | None
        voided_by_id: int | None
        created_by_id: int | None

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.void_reason = _clean_string(self.void_reason)

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="disease_catalog",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="initial_consultation",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="relapsed_from_case",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        _validate_related_object_belongs_to_pet(
            instance=self,
            errors=errors,
            related_field_name="initial_consultation",
        )

        _validate_related_object_belongs_to_pet(
            instance=self,
            errors=errors,
            related_field_name="relapsed_from_case",
        )

        if (
            self.relapsed_from_case_id is not None
            and self.pk is not None
            and self.relapsed_from_case_id == self.pk
        ):
            _add_error(
                errors,
                "relapsed_from_case",
                "A disease case cannot relapse from itself.",
            )

        if self.pet_id and self.disease_catalog_id:
            pet = _get_related_object(
                instance=self,
                related_field_name="pet",
            )

            disease_catalog = _get_related_object(
                instance=self,
                related_field_name="disease_catalog",
            )

            pet_species = getattr(pet, "species", None)
            pet_global_species_id = getattr(
                pet_species,
                "global_species_id",
                None,
            )
            disease_species_id = getattr(disease_catalog, "species_id", None)

            if (
                pet_global_species_id is not None
                and disease_species_id is not None
                and int(pet_global_species_id) != int(disease_species_id)
            ):
                _add_error(
                    errors,
                    "disease_catalog",
                    "Disease catalog species must match the pet species.",
                )

        if (
            self.is_chronic
            and self.disease_catalog_id
            and not self.disease_catalog.can_be_chronic
        ):
            _add_error(
                errors,
                "is_chronic",
                "This disease cannot be marked as chronic.",
            )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="resolved_at",
            actor_field="resolved_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="resolved_at",
            actor_field="resolved_by",
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

        if self.voided_at:
            if not self.void_reason:
                _add_error(
                    errors,
                    "void_reason",
                    "void_reason is required when voided_at is set.",
                )

            _raise_errors(errors)
            return

        if self.status == DISEASE_CASE_STATUS_ACTIVE and self.resolved_at:
            _add_error(
                errors,
                "resolved_at",
                "resolved_at must be null while case is ACTIVE.",
            )

        if self.status == DISEASE_CASE_STATUS_RESOLVED and not self.resolved_at:
            _add_error(
                errors,
                "resolved_at",
                "resolved_at is required when case is RESOLVED.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"{self.pet.name} — {self.disease_catalog.name}"


class Pet_Problem_Case(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Un problema clínico concreto detectado en un paciente.

    ACTIVE:
    El problema está presente o se está siguiendo actualmente.

    INACTIVE:
    El problema no se está siguiendo activamente, pero no necesariamente
    está resuelto clínicamente.

    RESOLVED:
    El problema terminó clínicamente y requiere resolved_at/resolved_by.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_PROBLEM_CASES_RN,
    )

    problem_catalog = models.ForeignKey(
        PROBLEM_CATALOG_MODEL,
        on_delete=models.PROTECT,
        related_name=PROBLEM_CATALOG_PROBLEM_CASES_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_PROBLEM_CASES_RN,
    )

    status = models.CharField(
        max_length=20,
        choices=Choices_Problem_Case_Status.choices,
        default=PROBLEM_CASE_STATUS_ACTIVE,
    )

    relapsed_from_case = models.ForeignKey(
        SELF,
        null=True,
        blank=True,
        related_name=RELAPSED_PROBLEM_CASES_RN,
        on_delete=models.PROTECT,
    )

    first_noted_date = models.DateField()

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        CENTER_STAFF_MEMBERSHIP_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CREATED_BY_PROBLEM_CASES_RN,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        problem_case_events: Any
        id: int
        pet_id: int
        problem_catalog_id: int
        veterinary_center_id: int
        relapsed_from_case_id: int | None
        resolved_by_id: int | None
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = [
            "-first_noted_date",
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "veterinary_center",
                    "pet",
                    "problem_catalog",
                    "first_noted_date",
                ],
                condition=Q(voided_at__isnull=True),
                name=UNIQUE_PROBLEM_CASE_PER_PET_PROBLEM_DATE_PER_CENTER,
            )
        ]

        indexes = [
            models.Index(
                fields=["pet", "status"],
                name=IDX_PROBLEM_CASE_PET_STATUS,
            ),
            models.Index(
                fields=["veterinary_center", "pet"],
                name=IDX_PROBLEM_CASE_CENTER_PET,
            ),
            models.Index(
                fields=["problem_catalog"],
                name=IDX_PROBLEM_CASE_CATALOG,
            ),
            models.Index(
                fields=["relapsed_from_case"],
                name=IDX_PROBLEM_CASE_RELAPSE,
            ),
            models.Index(
                fields=["pet", "first_noted_date"],
                name=IDX_PROBLEM_CASE_PET_FIRST_NOTED,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.void_reason = _clean_string(self.void_reason)

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="problem_catalog",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="relapsed_from_case",
        )

        _validate_related_object_belongs_to_pet(
            instance=self,
            errors=errors,
            related_field_name="relapsed_from_case",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        if (
            self.relapsed_from_case_id is not None
            and self.pk is not None
            and self.relapsed_from_case_id == self.pk
        ):
            _add_error(
                errors,
                "relapsed_from_case",
                "A problem case cannot relapse from itself.",
            )

        if self.pet_id and self.problem_catalog_id:
            pet = _get_related_object(
                instance=self,
                related_field_name="pet",
            )

            problem_catalog = _get_related_object(
                instance=self,
                related_field_name="problem_catalog",
            )

            pet_species = getattr(pet, "species", None)
            pet_global_species_id = getattr(
                pet_species,
                "global_species_id",
                None,
            )

            if pet_global_species_id is not None and problem_catalog is not None:
                allowed_species_ids = set(
                    problem_catalog.species.values_list("id", flat=True)
                )

                if (
                    allowed_species_ids
                    and int(pet_global_species_id) not in allowed_species_ids
                ):
                    _add_error(
                        errors,
                        "problem_catalog",
                        "Problem catalog species must include the pet species.",
                    )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="resolved_at",
            actor_field="resolved_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="resolved_at",
            actor_field="resolved_by",
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

        if self.voided_at:
            if not self.void_reason:
                _add_error(
                    errors,
                    "void_reason",
                    "void_reason is required when voided_at is set.",
                )

            _raise_errors(errors)
            return

        if self.status == PROBLEM_CASE_STATUS_ACTIVE:
            if self.resolved_at is not None:
                _add_error(
                    errors,
                    "resolved_at",
                    "resolved_at must be null while case is ACTIVE.",
                )

            if self.resolved_by_id is not None:
                _add_error(
                    errors,
                    "resolved_by",
                    "resolved_by must be null while case is ACTIVE.",
                )

        if self.status == PROBLEM_CASE_STATUS_INACTIVE:
            if self.resolved_at is not None:
                _add_error(
                    errors,
                    "resolved_at",
                    "resolved_at must be null while case is INACTIVE.",
                )

            if self.resolved_by_id is not None:
                _add_error(
                    errors,
                    "resolved_by",
                    "resolved_by must be null while case is INACTIVE.",
                )

        if self.status == PROBLEM_CASE_STATUS_RESOLVED:
            if self.resolved_at is None:
                _add_error(
                    errors,
                    "resolved_at",
                    "resolved_at is required when case is RESOLVED.",
                )

            if self.resolved_by_id is None:
                _add_error(
                    errors,
                    "resolved_by",
                    "resolved_by is required when case is RESOLVED.",
                )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"{self.pet.name} — {self.problem_catalog.name}"


class Pet_Disease_Event(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Evento clínico inmutable que construye la historia del caso de enfermedad.

    Only void fields can change after creation.
    """

    pet_disease_case = models.ForeignKey(
        PET_DISEASE_CASE_MODEL,
        on_delete=models.PROTECT,
        related_name=DISEASE_CASE_EVENTS_RN,
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CONSULTATION_DISEASE_EVENTS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_DISEASE_EVENTS_RN,
    )

    event_type = models.CharField(
        max_length=20,
        choices=Choices_Disease_Event_Type.choices,
    )

    event_date = models.DateTimeField(
        default=timezone.now,
    )

    severity = models.CharField(
        max_length=10,
        choices=Choices_Severity_Level.choices,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        pet_disease_case_id: int
        veterinary_center_id: int
        consultation_id: int | None
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = [
            "event_date",
            "id",
        ]

        indexes = [
            models.Index(
                fields=["pet_disease_case", "-event_date", "-id"],
                name=IDX_DISEASE_EVENT_CASE_TIMELINE,
            ),
            models.Index(
                fields=["veterinary_center", "-event_date", "-id"],
                name=IDX_DISEASE_EVENT_CENTER_TIMELINE,
            ),
            models.Index(
                fields=["consultation"],
                name=IDX_DISEASE_EVENT_CONSULTATION,
            ),
            models.Index(
                fields=["event_type"],
                name=IDX_DISEASE_EVENT_TYPE,
            ),
            models.Index(
                fields=["pet_disease_case", "event_type"],
                name=IDX_DISEASE_EVENT_CASE_TYPE,
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "pet_disease_case",
                    "event_type",
                    "event_date",
                    "consultation",
                ],
                condition=Q(voided_at__isnull=True),
                name=UNIQUE_DISEASE_EVENT_PER_CASE_TYPE_DATETIME_CONSULTATION,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.notes = _nullable_clean(self.notes)
        self.void_reason = _clean_string(self.void_reason)

        if self.pk:
            old_event = Pet_Disease_Event.objects.only(
                "pet_disease_case_id",
                "consultation_id",
                "veterinary_center_id",
                "event_type",
                "event_date",
                "severity",
                "notes",
                "created_by_id",
                "voided_at",
                "voided_by_id",
                "void_reason",
            ).get(pk=self.pk)

            immutable_fields_changed = (
                old_event.pet_disease_case_id != self.pet_disease_case_id
                or old_event.consultation_id != self.consultation_id
                or old_event.veterinary_center_id != self.veterinary_center_id
                or old_event.event_type != self.event_type
                or old_event.event_date != self.event_date
                or old_event.severity != self.severity
                or old_event.notes != self.notes
                or old_event.created_by_id != self.created_by_id
            )

            if immutable_fields_changed:
                _add_error(
                    errors,
                    "__all__",
                    "Disease events are immutable. Only void fields can be updated.",
                )

            if old_event.voided_at and not self.voided_at:
                _add_error(
                    errors,
                    "voided_at",
                    "A voided disease event cannot be unvoided.",
                )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet_disease_case",
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

        _validate_consultation_belongs_to_case_pet(
            instance=self,
            errors=errors,
            consultation_field_name="consultation",
            case_field_name="pet_disease_case",
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

        if self.voided_at and not self.void_reason:
            _add_error(
                errors,
                "void_reason",
                "void_reason is required when voided_at is set.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        return (
            f"{self.pet_disease_case.pet.name} — "
            f"{self.event_type} "
            f"({self.event_date:%Y-%m-%d %H:%M})"
        )


class Clinical_Comorbidity(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Agrupa comorbilidades clínicas de un paciente.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CLINICAL_COMORBIDITIES_RN,
    )

    disease_cases = models.ManyToManyField(
        PET_DISEASE_CASE_MODEL,
        related_name=DISEASE_CASES_CLINICAL_COMORBIDITIES_RN,
    )

    if TYPE_CHECKING:
        id: int
        pet_id: int

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pet"],
                name=UNIQUE_COMORBIDITY_PER_PET,
            )
        ]

    def clean(self) -> None:
        super().clean()

        if not self.pk:
            return

        for disease_case in self.disease_cases.all():
            if disease_case.pet_id != self.pet_id:
                raise ValidationError(
                    {
                        "disease_cases": (
                            "All disease cases must belong to the same pet."
                        ),
                    }
                )


class Pet_Problem_Event(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Evento clínico inmutable asociado al problema.
    Aparición, resolución, recaída, evolución, etc.

    Only void fields can change after creation.
    """

    pet_problem_case = models.ForeignKey(
        PET_PROBLEM_CASE_MODEL,
        on_delete=models.PROTECT,
        related_name=PROBLEM_CASE_PROBLEM_EVENTS_RN,
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CONSULTATION_PROBLEM_EVENTS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_PROBLEM_EVENTS_RN,
    )

    event_type = models.CharField(
        max_length=20,
        choices=Choices_Problem_Event_Type.choices,
    )

    event_date = models.DateTimeField(
        default=timezone.now,
    )

    notes = models.TextField(
        blank=True,
        null=True,
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        consultation_id: int | None
        pet_problem_case_id: int
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = [
            "-event_date",
            "-id",
        ]

        indexes = [
            models.Index(
                fields=["pet_problem_case", "-event_date", "-id"],
                name=IDX_PROBLEM_EVENT_CASE_DATE_ID,
            ),
            models.Index(
                fields=["veterinary_center", "-event_date"],
                name=IDX_PROBLEM_EVENT_CENTER_DATE,
            ),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "pet_problem_case",
                    "event_type",
                    "event_date",
                ],
                condition=Q(voided_at__isnull=True),
                name=UNIQUE_PROBLEM_EVENT_PER_CASE_TYPE_DATE,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.notes = _nullable_clean(self.notes)
        self.void_reason = _clean_string(self.void_reason)

        if self.pk:
            old_event = Pet_Problem_Event.objects.only(
                "pet_problem_case_id",
                "consultation_id",
                "veterinary_center_id",
                "event_type",
                "event_date",
                "notes",
                "created_by_id",
                "voided_at",
                "voided_by_id",
                "void_reason",
            ).get(pk=self.pk)

            immutable_fields_changed = (
                old_event.pet_problem_case_id != self.pet_problem_case_id
                or old_event.consultation_id != self.consultation_id
                or old_event.veterinary_center_id != self.veterinary_center_id
                or old_event.event_type != self.event_type
                or old_event.event_date != self.event_date
                or old_event.notes != self.notes
                or old_event.created_by_id != self.created_by_id
            )

            if immutable_fields_changed:
                _add_error(
                    errors,
                    "__all__",
                    "Problem events are immutable. Only void fields can be updated.",
                )

            if old_event.voided_at and not self.voided_at:
                _add_error(
                    errors,
                    "voided_at",
                    "A voided problem event cannot be unvoided.",
                )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet_problem_case",
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

        _validate_consultation_belongs_to_case_pet(
            instance=self,
            errors=errors,
            consultation_field_name="consultation",
            case_field_name="pet_problem_case",
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

        if self.voided_at and not self.void_reason:
            _add_error(
                errors,
                "void_reason",
                "void_reason is required when voided_at is set.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        return (
            f"{self.pet_problem_case} — "
            f"{self.event_type} "
            f"({self.event_date:%Y-%m-%d %H:%M})"
        )


class Critical_Case(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Marca estados críticos activos de un paciente.
    Estado clínico derivado de una condición o evento.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CRITICAL_CASES_RN,
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CRITICAL_CASES_RN,
    )

    disease_case = models.ForeignKey(
        PET_DISEASE_CASE_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name=DISEASE_CASE_CRITICAL_CASES_RN,
    )

    problem_case = models.ForeignKey(
        PET_PROBLEM_CASE_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name=PROBLEM_CASE_CRITICAL_CASES_RN,
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name=CONSULTATION_CRITICAL_CASES_RN,
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Choices_Critical_Case_Status.choices,
        default=CRITICAL_CASE_STATUS_ACTIVE,
    )

    started_at = models.DateTimeField(
        auto_now_add=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    resolved_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
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
        CENTER_STAFF_MEMBERSHIP_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CREATED_BY_CRITICAL_CASES_RN,
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
        veterinary_center_id: int
        disease_case_id: int | None
        problem_case_id: int | None
        consultation_id: int | None
        resolved_by_id: int | None
        voided_by_id: int | None
        created_by_id: int | None

    class Meta:
        ordering = [
            "-started_at",
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        disease_case__isnull=False,
                        problem_case__isnull=True,
                        consultation__isnull=True,
                    )
                    | models.Q(
                        disease_case__isnull=True,
                        problem_case__isnull=False,
                        consultation__isnull=True,
                    )
                    | models.Q(
                        disease_case__isnull=True,
                        problem_case__isnull=True,
                        consultation__isnull=False,
                    )
                ),
                name=CRITICAL_CASE_SINGLE_ORIGIN,
            ),
            models.UniqueConstraint(
                fields=["disease_case"],
                condition=models.Q(
                    disease_case__isnull=False,
                    status=CRITICAL_CASE_STATUS_ACTIVE,
                    voided_at__isnull=True,
                ),
                name=UNIQUE_ACTIVE_CRITICAL_CASE_PER_DISEASE_CASE,
            ),
            models.UniqueConstraint(
                fields=["problem_case"],
                condition=models.Q(
                    problem_case__isnull=False,
                    status=CRITICAL_CASE_STATUS_ACTIVE,
                    voided_at__isnull=True,
                ),
                name=UNIQUE_ACTIVE_CRITICAL_CASE_PER_PROBLEM_CASE,
            ),
            models.UniqueConstraint(
                fields=["consultation"],
                condition=models.Q(
                    consultation__isnull=False,
                    status=CRITICAL_CASE_STATUS_ACTIVE,
                    voided_at__isnull=True,
                ),
                name=UNIQUE_ACTIVE_CRITICAL_CASE_PER_CONSULTATION,
            ),
        ]

        indexes = [
            models.Index(fields=["status"], name=IDX_CRITICAL_STATUS),
            models.Index(fields=["pet", "status"], name=IDX_CRITICAL_PET_STATUS),
            models.Index(
                fields=["veterinary_center", "status"],
                name=IDX_CRITICAL_CENTER_STATUS,
            ),
        ]

    @property
    def is_active(self) -> bool:
        return (
            self.status == CRITICAL_CASE_STATUS_ACTIVE
            and self.voided_at is None
        )

    def apply_status_timestamps(self) -> None:
        """
        Explicit state-transition helper.

        Call this from commands/services before:
        - critical_case.full_clean()
        - critical_case.save()
        """

        if (
            self.status == CRITICAL_CASE_STATUS_RESOLVED
            and not self.resolved_at
        ):
            self.resolved_at = timezone.now()

        if self.status == CRITICAL_CASE_STATUS_ACTIVE:
            self.resolved_at = None
            self.resolved_by = None

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.reason = _clean_string(self.reason)
        self.void_reason = _clean_string(self.void_reason)

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="pet",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="disease_case",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="problem_case",
        )

        _validate_related_object_belongs_to_center(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_related_object_belongs_to_pet(
            instance=self,
            errors=errors,
            related_field_name="disease_case",
        )

        _validate_related_object_belongs_to_pet(
            instance=self,
            errors=errors,
            related_field_name="problem_case",
        )

        _validate_related_object_belongs_to_pet(
            instance=self,
            errors=errors,
            related_field_name="consultation",
        )

        _validate_audit_actors_belong_to_center(
            instance=self,
            errors=errors,
        )

        selected_origin_count = sum(
            origin_id is not None
            for origin_id in (
                self.disease_case_id,
                self.problem_case_id,
                self.consultation_id,
            )
        )

        if selected_origin_count != 1:
            _add_error(
                errors,
                "__all__",
                (
                    "A critical case must have exactly one origin: "
                    "disease_case, problem_case, or consultation."
                ),
            )

        if not self.reason:
            _add_error(
                errors,
                "reason",
                "Critical case reason is required.",
            )

        _validate_actor_requires_timestamp(
            instance=self,
            errors=errors,
            timestamp_field="resolved_at",
            actor_field="resolved_by",
        )

        _validate_timestamp_requires_actor(
            instance=self,
            errors=errors,
            timestamp_field="resolved_at",
            actor_field="resolved_by",
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

        if self.voided_at:
            if not self.void_reason:
                _add_error(
                    errors,
                    "void_reason",
                    "void_reason is required when voided_at is set.",
                )

            _raise_errors(errors)
            return

        if self.status == CRITICAL_CASE_STATUS_ACTIVE and self.resolved_at:
            _add_error(
                errors,
                "resolved_at",
                "resolved_at must be null while ACTIVE.",
            )

        if self.status == CRITICAL_CASE_STATUS_RESOLVED and not self.resolved_at:
            _add_error(
                errors,
                "resolved_at",
                "resolved_at is required when RESOLVED.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"Critical case {self.id} - Pet {self.pet_id}"


__all__ = [
    "Pet_History_Sequence",
    "Pet_Contact_Link",
    "Pet",
    "Pet_Disease_Case",
    "Pet_Problem_Case",
    "Pet_Disease_Event",
    "Clinical_Comorbidity",
    "Pet_Problem_Event",
    "Critical_Case",
]