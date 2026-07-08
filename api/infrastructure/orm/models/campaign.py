# api/infrastructure/orm/models/campaign.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max, Q
from django.utils import timezone

from api.shared.choices.choices import (
    Choices_Campaign_Actions,
    Choices_Campaign_Statuses,
    Choices_Sex,
)
from api.shared.constants.constants import (
    CAMPAIGN_ACTIONS_RN,
    CAMPAIGN_ENROLLMENTS_RN,
    CAMPAIGN_MODEL,
    CAMPAIGN_RESTRICTION_SETS_RN,
    CAMPAIGN_TARGETS_RN,
    CAMPAIGN_VALID_DATE_RANGE,
    CENTER_CAMPAIGN_ACTIONS_RN,
    CENTER_CAMPAIGN_ENROLLMENTS_RN,
    CENTER_CAMPAIGN_RESTRICTION_SETS_RN,
    CENTER_CAMPAIGN_TARGETS_RN,
    CENTER_CAMPAIGNS_RN,
    CONSULTATION_TYPE_MODEL,
    GLOBAL_BREED_MODEL,
    GLOBAL_SPECIES_MODEL,
    IDX_CAMPAIGN_CENTER_ACTIVE,
    IDX_CAMPAIGN_CENTER_START_DATE,
    IDX_CAMPAIGN_ENROLLMENT_CAMPAIGN,
    IDX_CAMPAIGN_ENROLLMENT_CENTER,
    IDX_CAMPAIGN_ENROLLMENT_PET,
    IDX_CAMPAIGN_ENROLLMENT_STATUS,
    PET_CAMPAIGN_ENROLLMENTS_RN,
    PET_MODEL,
    PROCEDURE_TYPE_MODEL,
    UNIQUE_ACTIVE_RESTRICTION_SET_PER_CAMPAIGN,
    UNIQUE_CAMPAIGN_CODE_PER_CENTER,
    UNIQUE_CAMPAIGN_CONSULTATION_ACTION,
    UNIQUE_CAMPAIGN_ENROLLMENTS,
    UNIQUE_CAMPAIGN_PROCEDURE_ACTION,
    UNIQUE_CAMPAIGN_RESTRICTION_SET_VERSION,
    UNIQUE_CAMPAIGN_TARGET_DEFINITION,
    UNIQUE_CAMPAIGN_VACCINE_ACTION,
    VACCINE_TYPE_MODEL,
    VETERINARY_CENTER_MODEL,
    CENTER_STAFF_MEMBERSHIP_MODEL,
)
from api.shared.orm.audit_mixins import (
    DeactivationAuditValidationMixin,
    SoftDeleteAuditValidationMixin,
)
from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin


# Models located in api/infrastructure/orm/models/campaign.py:
# - Campaign
# - Campaign_Action
# - Campaign_Target
# - Campaign_Restriction_Set
# - Campaign_Enrollment


CAMPAIGN_ACTION_VACCINE: str = Choices_Campaign_Actions.VACCINE.value
CAMPAIGN_ACTION_PROCEDURE: str = Choices_Campaign_Actions.PROCEDURE.value
CAMPAIGN_ACTION_CONSULTATION: str = Choices_Campaign_Actions.CONSULTATION.value

CAMPAIGN_STATUS_SCHEDULED: str = Choices_Campaign_Statuses.SCHEDULED.value


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
    related_id = getattr(instance, f"{related_field_name}_id", None)

    if center_id is None or related_id is None:
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
                "center as this record."
            ),
        )


def _validate_actor_fields_belong_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
) -> None:
    """
    Validates actor fields that remain as current-row convenience/state fields.

    Detailed audit history belongs in Audit_Log.
    These fields are only for direct current-state access.
    """

    for actor_field_name in (
        "created_by",
        "soft_deleted_by",
        "deactivated_by",
    ):
        if not hasattr(instance, f"{actor_field_name}_id"):
            continue

        _validate_related_object_belongs_to_center(
            instance=instance,
            errors=errors,
            related_field_name=actor_field_name,
        )


def _validate_campaign_belongs_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
) -> None:
    campaign_id = getattr(instance, "campaign_id", None)
    veterinary_center_id = getattr(instance, "veterinary_center_id", None)

    if campaign_id is None or veterinary_center_id is None:
        return

    campaign = _get_related_object(
        instance=instance,
        related_field_name="campaign",
    )

    campaign_center_id = getattr(campaign, "veterinary_center_id", None)

    if campaign_center_id is None:
        return

    if int(campaign_center_id) != int(veterinary_center_id):
        _add_error(
            errors,
            "campaign",
            "La campaña pertenece a otro centro veterinario.",
        )


def _validate_pet_belongs_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
) -> None:
    pet_id = getattr(instance, "pet_id", None)
    veterinary_center_id = getattr(instance, "veterinary_center_id", None)

    if pet_id is None or veterinary_center_id is None:
        return

    pet = _get_related_object(
        instance=instance,
        related_field_name="pet",
    )

    pet_center_id = getattr(pet, "veterinary_center_id", None)

    if pet_center_id is None:
        return

    if int(pet_center_id) != int(veterinary_center_id):
        _add_error(
            errors,
            "pet",
            "El paciente pertenece a otro centro veterinario.",
        )


class Campaign(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Represents a clinical campaign organized by a veterinary center.

    Examples:
    - vaccination
    - sterilization
    - deworming
    - checkup
    - custom clinical campaign

    Aggregate root of the campaign module.

    Audit policy:
    - created_at / updated_at stay on the row.
    - soft_deleted_at / soft_deleted_by stay on the row as current state.
    - detailed who/what/why before/after history belongs in Audit_Log.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CAMPAIGNS_RN,
    )

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de término. Null significa indefinida.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Permite desactivar la campaña sin eliminarla.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    soft_deleted_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["-start_date", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=Q(soft_deleted_at__isnull=True),
                name=UNIQUE_CAMPAIGN_CODE_PER_CENTER,
            ),
            models.CheckConstraint(
                condition=(
                    Q(end_date__isnull=True)
                    | Q(end_date__gte=models.F("start_date"))
                ),
                name=CAMPAIGN_VALID_DATE_RANGE,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active", "soft_deleted_at"],
                name=IDX_CAMPAIGN_CENTER_ACTIVE,
            ),
            models.Index(
                fields=["veterinary_center", "start_date"],
                name=IDX_CAMPAIGN_CENTER_START_DATE,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        raw_code = cast(str | None, getattr(self, "code", None))
        raw_name = cast(str | None, getattr(self, "name", None))

        self.code = (raw_code or "").strip().upper()
        self.name = (raw_name or "").strip()

        start_date = getattr(self, "start_date", None)
        end_date = getattr(self, "end_date", None)

        if (
            end_date is not None
            and start_date is not None
            and end_date < start_date
        ):
            _add_error(
                errors,
                "end_date",
                "La fecha de término no puede ser anterior a la fecha de inicio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        code = cast(str, getattr(self, "code", ""))
        name = cast(str, getattr(self, "name", ""))

        return f"{code} - {name}"


class Campaign_Action(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Defines one clinical action expected from a campaign.

    Detailed changes are audited through Audit_Log.
    """

    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_ACTIONS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CAMPAIGN_ACTIONS_RN,
    )

    action = models.CharField(
        max_length=30,
        choices=Choices_Campaign_Actions.choices,
    )

    vaccine_action = models.ForeignKey(
        VACCINE_TYPE_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    procedure_action = models.ForeignKey(
        PROCEDURE_TYPE_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    consultation_action = models.ForeignKey(
        CONSULTATION_TYPE_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    soft_deleted_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        campaign_id: int
        veterinary_center_id: int
        vaccine_action_id: int | None
        procedure_action_id: int | None
        consultation_action_id: int | None
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "action", "vaccine_action"],
                condition=(
                    Q(soft_deleted_at__isnull=True)
                    & Q(action=CAMPAIGN_ACTION_VACCINE)
                    & Q(vaccine_action__isnull=False)
                ),
                name=UNIQUE_CAMPAIGN_VACCINE_ACTION,
            ),
            models.UniqueConstraint(
                fields=["campaign", "action", "procedure_action"],
                condition=(
                    Q(soft_deleted_at__isnull=True)
                    & Q(action=CAMPAIGN_ACTION_PROCEDURE)
                    & Q(procedure_action__isnull=False)
                ),
                name=UNIQUE_CAMPAIGN_PROCEDURE_ACTION,
            ),
            models.UniqueConstraint(
                fields=["campaign", "action", "consultation_action"],
                condition=(
                    Q(soft_deleted_at__isnull=True)
                    & Q(action=CAMPAIGN_ACTION_CONSULTATION)
                    & Q(consultation_action__isnull=False)
                ),
                name=UNIQUE_CAMPAIGN_CONSULTATION_ACTION,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_campaign_belongs_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        action = cast(str | None, getattr(self, "action", None))

        if action == CAMPAIGN_ACTION_VACCINE:
            if not self.vaccine_action_id:
                _add_error(
                    errors,
                    "vaccine_action",
                    "La acción de vacuna es obligatoria.",
                )

            if self.procedure_action_id or self.consultation_action_id:
                _add_error(
                    errors,
                    "action",
                    (
                        "Una acción de vacuna no puede tener procedimiento "
                        "ni consulta asociados."
                    ),
                )

        elif action == CAMPAIGN_ACTION_PROCEDURE:
            if not self.procedure_action_id:
                _add_error(
                    errors,
                    "procedure_action",
                    "La acción de procedimiento es obligatoria.",
                )

            if self.vaccine_action_id or self.consultation_action_id:
                _add_error(
                    errors,
                    "action",
                    (
                        "Una acción de procedimiento no puede tener vacuna "
                        "ni consulta asociadas."
                    ),
                )

        elif action == CAMPAIGN_ACTION_CONSULTATION:
            if not self.consultation_action_id:
                _add_error(
                    errors,
                    "consultation_action",
                    "La acción de consulta es obligatoria.",
                )

            if self.vaccine_action_id or self.procedure_action_id:
                _add_error(
                    errors,
                    "action",
                    (
                        "Una acción de consulta no puede tener vacuna "
                        "ni procedimiento asociados."
                    ),
                )

        _raise_errors(errors)


class Campaign_Target(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Defines the clinical target audience of a campaign.

    This works as the initial structural filter to determine which patients
    are eligible for a campaign.

    Detailed changes are audited through Audit_Log.
    """

    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_TARGETS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CAMPAIGN_TARGETS_RN,
    )

    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    breed = models.ForeignKey(
        GLOBAL_BREED_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    sex = models.CharField(
        max_length=1,
        choices=Choices_Sex.choices,
        null=True,
        blank=True,
    )

    min_age_months = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    max_age_months = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    sterilized = models.BooleanField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    soft_deleted_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        campaign_id: int
        veterinary_center_id: int
        species_id: int | None
        breed_id: int | None
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        verbose_name = "Campaign target"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "campaign",
                    "species",
                    "breed",
                    "sex",
                    "min_age_months",
                    "max_age_months",
                    "sterilized",
                ],
                condition=Q(soft_deleted_at__isnull=True),
                nulls_distinct=False,
                name=UNIQUE_CAMPAIGN_TARGET_DEFINITION,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        min_age_months = cast(int | None, getattr(self, "min_age_months", None))
        max_age_months = cast(int | None, getattr(self, "max_age_months", None))

        if (
            min_age_months is not None
            and max_age_months is not None
            and min_age_months > max_age_months
        ):
            _add_error(
                errors,
                "min_age_months",
                "La edad mínima no puede ser mayor que la edad máxima.",
            )

        if self.breed_id and self.species_id:
            breed = _get_related_object(
                instance=self,
                related_field_name="breed",
            )

            breed_species_id = getattr(breed, "species_id", None)

            if breed_species_id is not None and breed_species_id != self.species_id:
                _add_error(
                    errors,
                    "breed",
                    "La raza debe pertenecer a la especie seleccionada.",
                )

        _validate_campaign_belongs_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)


class Campaign_Restriction_Set(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    DeactivationAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Versioned campaign restriction rules.

    This model keeps deactivation state on the row.
    The deactivation reason and before/after details belong in Audit_Log.
    """

    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_RESTRICTION_SETS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CAMPAIGN_RESTRICTION_SETS_RN,
    )

    version = models.PositiveIntegerField()

    rules = models.JSONField()

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    deactivated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    deactivated_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    soft_deleted_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        campaign_id: int
        veterinary_center_id: int
        created_by_id: int | None
        deactivated_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["-version"]

        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "version"],
                name=UNIQUE_CAMPAIGN_RESTRICTION_SET_VERSION,
            ),
            models.UniqueConstraint(
                fields=["campaign"],
                condition=Q(is_active=True, soft_deleted_at__isnull=True),
                name=UNIQUE_ACTIVE_RESTRICTION_SET_PER_CAMPAIGN,
            ),
        ]

        indexes = [
            models.Index(
                fields=["campaign", "is_active", "soft_deleted_at"],
            ),
            models.Index(
                fields=["veterinary_center"],
            ),
        ]

    @classmethod
    def get_next_version_for_campaign(cls, campaign_id: int) -> int:
        last_version = (
            cls.objects.filter(campaign_id=campaign_id)
            .aggregate(max_version=Max("version"))
            .get("max_version")
        )

        return 1 if last_version is None else last_version + 1

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_campaign_belongs_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        if self.soft_deleted_at is not None and self.deactivated_at is not None:
            _add_error(
                errors,
                "soft_deleted_at",
                (
                    "Un conjunto de restricciones no debe estar eliminado "
                    "y desactivado al mismo tiempo."
                ),
            )

        _raise_errors(errors)


class Campaign_Enrollment(
    TrimFieldsMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Represents the concrete enrollment of a patient in a campaign.

    This is an operational/history record.
    It must protect both campaign and pet from accidental hard deletion.

    Detailed changes are audited through Audit_Log.
    """

    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.PROTECT,
        related_name=CAMPAIGN_ENROLLMENTS_RN,
    )

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.PROTECT,
        related_name=PET_CAMPAIGN_ENROLLMENTS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CAMPAIGN_ENROLLMENTS_RN,
    )

    status = models.CharField(
        max_length=20,
        choices=Choices_Campaign_Statuses.choices,
        default=CAMPAIGN_STATUS_SCHEDULED,
    )

    exclusion_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    enrolled_at = models.DateTimeField(
        default=timezone.now,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBERSHIP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        campaign_id: int
        pet_id: int
        veterinary_center_id: int
        created_by_id: int | None

    class Meta:
        ordering = ["-enrolled_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "pet"],
                name=UNIQUE_CAMPAIGN_ENROLLMENTS,
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center"],
                name=IDX_CAMPAIGN_ENROLLMENT_CENTER,
            ),
            models.Index(
                fields=["campaign"],
                name=IDX_CAMPAIGN_ENROLLMENT_CAMPAIGN,
            ),
            models.Index(
                fields=["pet"],
                name=IDX_CAMPAIGN_ENROLLMENT_PET,
            ),
            models.Index(
                fields=["status"],
                name=IDX_CAMPAIGN_ENROLLMENT_STATUS,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_campaign_belongs_to_center(
            instance=self,
            errors=errors,
        )

        _validate_pet_belongs_to_center(
            instance=self,
            errors=errors,
        )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        enrolled_at = getattr(self, "enrolled_at", None)
        completed_at = getattr(self, "completed_at", None)

        if (
            completed_at is not None
            and enrolled_at is not None
            and completed_at < enrolled_at
        ):
            _add_error(
                errors,
                "completed_at",
                "La fecha de finalización no puede ser anterior a la fecha de inscripción.",
            )

        _raise_errors(errors)

    def __str__(self) -> str:
        pet = cast(Any, self.pet)
        campaign = cast(Any, self.campaign)
        status = cast(str, getattr(self, "status", ""))

        return f"{pet} → {campaign} ({status})"


__all__ = [
    "Campaign",
    "Campaign_Action",
    "Campaign_Target",
    "Campaign_Restriction_Set",
    "Campaign_Enrollment",
]