# api/infrastructure/orm/models/campaign.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import TYPE_CHECKING, Any
from django.db.models import Q

from api.shared.choices.choices import (
    Choices_CampaignActions,
    Choices_CampaignStatuses,
    Choices_Sex,
)

from api.shared.constants.constants import *

from api.shared.http.mixins import TrimFieldsMixin

# Models located in api/infrastructure/orm/models/campaign.py:
# Models: Campaign, Campaign_Action, Campaign_Target, Campaign_Restriction_Set, Campaign_Enrollment,

class Campaign(TrimFieldsMixin, models.Model):
    """
    Propósito: Representa una campaña clínica organizada por el centro veterinario 
    (vacunación, esterilización, desparasitación, chequeo u otra personalizada).
    
    Aggregate root del módulo de campañas. Define el contexto, vigencia y control
    operativo de una estrategia sanitaria.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CAMPAIGNS_RN,
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de término. Null significa indefinida."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Permite desactivar la campaña sin eliminarla."
    )
    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CREATED_BY_CAMPAIGNS_RN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                name=UNIQUE_CAMPAIGN_CODE_PER_CENTER
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(end_date__isnull=True) |
                    models.Q(end_date__gte=models.F("start_date"))
                ),
                name=CAMPAIGN_VALID_DATE_RANGE
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active"],
                name=IDX_CAMPAIGN_CENTER_ACTIVE
            ),
            models.Index(
                fields=["veterinary_center", "start_date"],
                name=IDX_CAMPAIGN_CENTER_START_DATE
            ),
        ]

    def save(self, *args: Any, **kwargs: Any):
        if self.code:
            self.code = self.code.strip().upper()
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"

    
class Campaign_Action(models.Model):
    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_ACTIONS_RN,
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CAMPAIGN_ACTIONS_RN
    )
    action = models.CharField(
        max_length=30,
        choices=Choices_CampaignActions.choices,
    )
    vaccine_action = models.ForeignKey(
        VACCINE_TYPE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    procedure_action = models.ForeignKey(
        PROCEDURE_TYPE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    consultation_action = models.ForeignKey(
        CONSULTATION_TYPE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "action", "vaccine_action"],
                name=UNIQUE_CAMPAIGN_VACCINE_ACTION
            ),
            models.UniqueConstraint(
                fields=["campaign", "action", "procedure_action"],
                name=UNIQUE_CAMPAIGN_PROCEDURE_ACTION
            ),
            models.UniqueConstraint(
                fields=["campaign", "action", "consultation_action"],
                name=UNIQUE_CAMPAIGN_CONSULTATION_ACTION
            ),
        ]
        
    def clean(self):
        if self.action == Choices_CampaignActions.VACCINE:
            if not self.vaccine_action:
                raise ValidationError("vaccine_action requerido")
            if self.procedure_action or self.consultation_action:
                raise ValidationError("Campos incompatibles")
        elif self.action == Choices_CampaignActions.PROCEDURE:
            if not self.procedure_action:
                raise ValidationError("procedure_action requerido")
            if self.vaccine_action or self.consultation_action:
                raise ValidationError("Campos incompatibles")
        elif self.action == Choices_CampaignActions.CONSULTATION:
            if not self.consultation_action:
                raise ValidationError("consultation_action requerido")
            if self.vaccine_action or self.procedure_action:
                raise ValidationError("Campos incompatibles")
            
    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)

    
class Campaign_Target(models.Model):
    """
    Propósito: Define el público objetivo clínico de una campaña.
    Funciona como filtro estructural inicial para determinar qué pacientes son elegibles.
    """

    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_TARGETS_RN,
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CAMPAIGN_TARGETS_RN,
    )
    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    breed = models.ForeignKey(
        GLOBAL_BREED_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    sex = models.CharField(
        max_length=1,
        choices=Choices_Sex.choices,
        null=True,
        blank=True,
    )
    min_age_months = models.PositiveIntegerField(null=True, blank=True)
    max_age_months = models.PositiveIntegerField(null=True, blank=True)
    sterilized = models.BooleanField(null=True, blank=True)
    
    if TYPE_CHECKING:
        species_id: int | None
        veterinary_center_id: int
    
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
                name=UNIQUE_CAMPAIGN_TARGET_DEFINITION
            )
        ]

    def clean(self):
        if (
            self.min_age_months is not None
            and self.max_age_months is not None
            and self.min_age_months > self.max_age_months
        ):
            raise ValidationError(
                "min_age_months no puede ser mayor que max_age_months"
            )
        if self.breed and self.species:

            if self.breed.species_id != self.species_id:
                raise ValidationError(
                    "La raza debe pertenecer a la especie"
                )
        if self.campaign:
            if (
                self.campaign.veterinary_center_id
                != self.veterinary_center_id
            ):
                raise ValidationError(
                    "Campaign pertenece a otro veterinary_center"
                )
        if self.species:
            if (
                self.species.veterinary_center_id
                != self.veterinary_center_id
            ):
                raise ValidationError(
                    "Species pertenece a otro veterinary_center"
                )
        if self.breed:
            if (
                self.breed.species.veterinary_center_id
                != self.veterinary_center_id
            ):
                raise ValidationError(
                    "Breed pertenece a otro veterinary_center"
                )
                
    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)

class Campaign_Restriction_Set(TrimFieldsMixin, models.Model):
    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_RESTRICTION_SETS_RN
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CAMPAIGN_RESTRICTION_SETS_RN
    )
    version = models.PositiveIntegerField()
    rules = models.JSONField()
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CREATED_BY_CAMPAIGN_RESTRICTION_SETS_RN
    )
    created_at = models.DateTimeField(auto_now_add=True)
        
    if TYPE_CHECKING:
        campaign_id: int
        veterinary_center_id: int

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "version"],
                name=UNIQUE_CAMPAIGN_RESTRICTION_SET_VERSION
            ),
            models.UniqueConstraint(
                fields=["campaign"],
                condition=Q(is_active=True),
                name=UNIQUE_ACTIVE_RESTRICTION_SET_PER_CAMPAIGN
            )
        ]

        indexes = [
            models.Index(fields=["campaign", "is_active"]),
            models.Index(fields=["veterinary_center"])
        ]
        
    def clean(self):
        if self.campaign_id and self.veterinary_center_id:
            if self.campaign.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    "Campaign pertenece a otro veterinary_center."
                )
        
    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        if self._state.adding:
            last_version = (
                Campaign_Restriction_Set.objects
                .filter(campaign=self.campaign)
                .aggregate(models.Max("version"))
                .get("version__max")
            )
            self.version = 1 if last_version is None else last_version + 1

        super().save(*args, **kwargs)

    
class Campaign_Enrollment(TrimFieldsMixin, models.Model):
    """
    Propósito: Representa la inscripción concreta de un paciente en una campaña.
    
    it will expose an action in services/campaign/commands.py:
    
    # api/services/campaign/commands.py
    
    def complete_enrollment(enrollment: Campaign_Enrollment) -> Campaign_Enrollment:

        enrollment.status = Choices_CampaignStatuses.COMPLETED
        enrollment.completed_at = timezone.now()

        enrollment.save(
            update_fields=[
                "status",
                "completed_at",
                "updated_at",
            ]
        )

        return enrollment


    def exclude_enrollment(
        enrollment: Campaign_Enrollment,
        reason: str
    ) -> Campaign_Enrollment:

        enrollment.status = Choices_CampaignStatuses.EXCLUDED
        enrollment.exclusion_reason = reason
        enrollment.completed_at = timezone.now()

        enrollment.save(
            update_fields=[
                "status",
                "exclusion_reason",
                "completed_at",
                "updated_at",
            ]
        )

        return enrollment
    """
    campaign = models.ForeignKey(
        CAMPAIGN_MODEL,
        on_delete=models.CASCADE,
        related_name=CAMPAIGN_ENROLLMENTS_RN,
    )
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_CAMPAIGN_ENROLLMENTS_RN,
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CAMPAIGN_ENROLLMENTS_RN,
    )
    status = models.CharField(
        max_length=20,
        choices=Choices_CampaignStatuses.choices,
        default=Choices_CampaignStatuses.SCHEDULED,
    )
    exclusion_reason = models.CharField(
        max_length=255,
        blank=True,
    )
    enrolled_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        campaign_id: int | None
        pet_id: int | None
        veterinary_center_id: int | None

    class Meta:
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "pet"],
                name=UNIQUE_CAMPAIGN_ENROLLMENTS
            )
        ]
        indexes = [
            models.Index(
                fields=["veterinary_center"],
                name=IDX_CAMPAIGN_ENROLLMENT_CENTER
            ),
            models.Index(
                fields=["campaign"],
                name=IDX_CAMPAIGN_ENROLLMENT_CAMPAIGN
            ),
            models.Index(
                fields=["pet"],
                name=IDX_CAMPAIGN_ENROLLMENT_PET
            ),
            models.Index(
                fields=["status"],
                name=IDX_CAMPAIGN_ENROLLMENT_STATUS
            ),
        ]

    def clean(self):
        if self.campaign_id and self.veterinary_center_id:
            if self.campaign.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    "Campaign pertenece a otro veterinary_center."
                )
        if self.pet_id and self.veterinary_center_id:
            if self.pet.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    "Pet pertenece a otro veterinary_center."
                )
                
    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)
                
    def __str__(self):
        return f"{self.pet} → {self.campaign} ({self.status})"
    
__all__ = [
    "Campaign", 
    "Campaign_Action", 
    "Campaign_Target", 
    "Campaign_Restriction_Set", 
    "Campaign_Enrollment", 
]