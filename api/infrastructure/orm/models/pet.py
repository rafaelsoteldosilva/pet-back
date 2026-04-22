# api/infrastructure/orm/models/patient.py

# Models in api/infrastructure/orm/models/pet.py:
# Pet_History_Sequence, Pet_Contact, Pet, Pet_Disease_Case, Pet_Problem_Case, Pet_Disease_Event, Clinical_Comorbidity, Pet_Problem_Event,
# Critical_Case, 

from datetime import date
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction, IntegrityError
from typing import Any, TYPE_CHECKING, Optional, cast
from django.db.models import Q

from api.shared.utils.microchip_validator import microchip_validator

from api.shared.choices.choices import (
    Choices_ContactRelationship,
    Choices_CriticalCaseStatus,
    Choices_DiseaseEventType,
    Choices_PetClinicalRecordStatus,
    Choices_PetContactRole,
    Choices_PetStatus,
    Choices_ProblemEventType,
    Choices_DiseaseCaseStatus,
    Choices_ProblemCaseStatus,
    Choices_Sex,
    Choices_Size,
    Choices_SeverityLevel,
)

from api.shared.constants.constants import *

from api.shared.http.mixins import TrimFieldsMixin

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .clinical import Consultation
    

class Pet_History_Sequence(models.Model):
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
    )
    year = models.IntegerField()
    last_value = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "year"],
                name="uniq_pet_history_seq_center_year",
            )
        ]
        
class Pet_Contact(models.Model):
    """
    Relación entre un paciente y un contacto con un rol específico.
    Permite múltiples roles sin modificar el schema del Pet.
    """

    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_CONTACTS_RN,
    )

    contact = models.ForeignKey(
        CONTACT_MODEL,
        on_delete=models.CASCADE,
        related_name=CONTACT_PET_CONTACTS_RN,
    )
    
    relationship = models.CharField(
        "relationship to pet or its owner",
        max_length=20,
        choices=Choices_ContactRelationship.choices,
        null=True,
        blank=True,
        help_text="Personal relationship of the contact to the pet or to the pet's owner (e.g., family member, neighbor, caretaker)."
    )
    
    role = models.CharField(
        max_length=20,
        choices=Choices_PetContactRole.choices,
        db_index=True,
    )

    is_primary_contact = models.BooleanField(
        default=False,
        help_text="Primary contact for this role",
    )

    notes = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    if TYPE_CHECKING:
        id: int
        pet_id: int
        contact_id: int

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pet", "contact", "role"],
                name="unique_pet_contact_role",
            ),

            # Solo un primary por rol
            models.UniqueConstraint(
                fields=["pet", "role"],
                condition=Q(is_primary_contact=True),
                name="unique_primary_contact_per_role",
            ),
        ]

        indexes = [
            models.Index(fields=["pet", "role"]),
            models.Index(fields=["contact"]),
        ]

    def clean(self):
        super().clean()

        # seguridad: evitar contacto duplicado con mismo rol
        if not self.pet_id or not self.contact_id:
            return

        qs = Pet_Contact.objects.filter(
            pet=self.pet,
            contact=self.contact,
            role=self.role,
        )

        if self.pk:
            qs = qs.exclude(pk=self.pk)

        if qs.exists():
            raise ValidationError(
                "This contact already has this role for this pet."
            )

    def __str__(self):
        return f"{self.pet.name} — {self.contact} ({self.role})"

class Pet(TrimFieldsMixin, models.Model):
    """
    Propósito: Paciente veterinario. Núcleo clínico del sistema.
    """
    history_code = models.CharField(
        max_length=50,
        db_index=True,
        editable=False,
    )
    name = models.CharField(max_length=100, db_index=True)
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

    sterilized = models.BooleanField(default=False)

    birth_date = models.DateField(blank=True, null=True)

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
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=LAST_ATTENDING_VET_PETS_RN,
    )

    reference = models.CharField(max_length=100, blank=True, default="")

    has_pedigree = models.BooleanField(default=False)

    pedigree_registry = models.CharField(
        max_length=50,
        blank=True,
        null=True,
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

    has_microchip = models.BooleanField(default=False)

    microchip_code = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        validators=[microchip_validator],
        db_index=True,
    )

    microchip_date = models.DateField(blank=True, null=True)

    microchip_region = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    observations = models.TextField(blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    photo_url = models.URLField(blank=True, null=True)

    contacts = models.ManyToManyField(
        CONTACT_MODEL,
        through="Pet_Contact",
        related_name=CONTACTS_PETS_RN,
        blank=True,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.RESTRICT,
    )

    status = models.CharField(
        max_length=16,
        choices=Choices_PetStatus.choices,
        default=Choices_PetStatus.ACTIVE,
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
        help_text="When the patient was archived (read-only)",
    )

    clinical_record_status = models.CharField(
        max_length=20,
        choices=Choices_PetClinicalRecordStatus.choices,
        default=Choices_PetClinicalRecordStatus.DRAFT,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    master_pet = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=MERGED_PET_PETS_RN,
        help_text="If this pet was merged into another patient",
    )

    merged_at = models.DateTimeField(null=True, blank=True)

    merged_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=MERGED_BY_PETS_RN,
    )

    if TYPE_CHECKING:
        id: int
        species_id: int
        breed_id: Optional[int]
        veterinary_center_id: int
        last_attending_vet_id: Optional[int]
        pet_contacts: models.Manager["Pet_Contact"]
        pet_disease_cases: models.Manager["Pet_Disease_Case"]
        pet_problem_cases: models.Manager["Pet_Problem_Case"]
        pet_consultations: models.Manager["Consultation"]
        master_pet_id: Optional[int]

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
            models.Index(fields=["veterinary_center", "species", "breed"]),
            models.Index(fields=["veterinary_center", "microchip_code"]),
        ]

    # -----------------------------------------------------
    # CONTACT HELPERS
    # -----------------------------------------------------

    @property
    def owners(self):
        return self.pet_contacts.filter(role="OWNER")

    @property
    def responsible_contacts(self):
        return self.pet_contacts.filter(role="RESPONSIBLE")

    @property
    def emergency_contacts(self):
        return self.pet_contacts.filter(role="EMERGENCY")

    @property
    def primary_owner(self):
        rel = self.pet_contacts.filter(
            role="OWNER",
            is_primary_contact=True,
        ).select_related("contact").first()
        return rel.contact if rel else None

    # -----------------------------------------------------
    # MERGE LOGIC
    # -----------------------------------------------------

    @property
    def master(self) -> "Pet":
        pet: "Pet" = self
        visited: set[int] = set()

        while pet.master_pet_id is not None:
            if pet.pk is not None:
                if pet.pk in visited:
                    break
                visited.add(pet.pk)

            pet = pet.master_pet  # type: ignore

        return pet

    @property
    def is_master(self) -> bool:
        return self.master_pet_id is None

    @property
    def is_merged(self) -> bool:
        return self.master_pet_id is not None

    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    @property
    def age(self) -> Optional[int]:
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
        return (
            self.clinical_record_status
            == cast(str, Choices_PetClinicalRecordStatus.DRAFT)
        )

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    def save(self, *args: Any, **kwargs: Any):

        if self.pk is None and not self.history_code:
            with transaction.atomic():

                year = timezone.now().year

                try:
                    seq, _ = (
                        Pet_History_Sequence.objects
                        .select_for_update()
                        .get_or_create(
                            veterinary_center=self.veterinary_center,
                            year=year,
                            defaults={"last_value": 0},
                        )
                    )

                except IntegrityError:

                    seq = (
                        Pet_History_Sequence.objects
                        .select_for_update()
                        .get(
                            veterinary_center=self.veterinary_center,
                            year=year,
                        )
                    )

                seq.last_value += 1
                seq.save(update_fields=["last_value"])

                center = self.veterinary_center

                self.history_code = (
                    f"{center.country_code}-"
                    f"{center.clinic_code}-"
                    f"{year}-"
                    f"{seq.last_value:05d}"
                )

        self.full_clean()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.species.name})"
    

class Pet_Disease_Case(TrimFieldsMixin, models.Model):
    """
    Propósito: Un caso clínico de enfermedad en un paciente. Vive en el tiempo.
    If it's name is changed, change Pet also
    """
    pet = models.ForeignKey(
        PET_MODEL, 
        on_delete=models.CASCADE, 
        related_name=PET_DISEASE_CASES_RN)
    
    disease_catalog = models.ForeignKey(
        DISEASE_CATALOG_MODEL,
        on_delete=models.PROTECT,
        related_name=DISEASE_CATALOG_CASES_RN
    )
    relapsed_from_case = models.ForeignKey(
        SELF,
        null=True,
        blank=True,
        related_name=RELAPSED_DISEASE_CASES_RN,
        on_delete=models.SET_NULL
    ) 
    diagnosis_date = models.DateField()
    initial_consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=INITIAL_CONSULTATION_DISEASE_CASES_RN
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_DISEASE_CASES_RN
    )

    status = models.CharField(
        max_length=20,
        choices=Choices_DiseaseCaseStatus.choices,
        default=Choices_DiseaseCaseStatus.ACTIVE,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=RESOLVED_BY_DISEASE_CASES_RN,
    )

    is_chronic = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CREATED_BY_DISEASE_CASES_RN,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        disease_case_events: Any
        id: int

    def clean(self):
        super().clean()

        if self.pet.veterinary_center != self.veterinary_center:
            raise ValidationError("Pet does not belong to this center.")

        if self.disease_catalog.veterinary_center != self.veterinary_center:
            raise ValidationError("Disease catalog does not belong to this center.")

        if self.is_chronic and not self.disease_catalog.can_be_chronic:
            raise ValidationError("This disease cannot be marked as chronic.")
      
        if self.status == cast(str, Choices_DiseaseCaseStatus.ACTIVE) and self.resolved_at:
            raise ValidationError("resolved_at must be null while case is ACTIVE.")

        if self.status == cast(str, Choices_DiseaseCaseStatus.RESOLVED) and not self.resolved_at:
            raise ValidationError("resolved_at is required when case is RESOLVED.")

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        if not self.diagnosis_date:
            self.diagnosis_date = timezone.now().date()
        super().save(*args, **kwargs)
        
class Pet_Problem_Case(models.Model):
    """
    Propósito: Un problema clínico concreto detectado en un paciente.
    If it's name is changed, change Pet also
    """
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
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
        related_name=CENTER_PROBLEM_CASES_RN
    )
    status = models.CharField(
        max_length=20,
        choices=Choices_ProblemCaseStatus.choices,
        default=Choices_ProblemCaseStatus.ACTIVE,
    )
    relapsed_from_case = models.ForeignKey(
        SELF,
        null=True,
        blank=True,
        related_name=RELAPSED_PROBLEM_CASES_RN,
        on_delete=models.SET_NULL
    ) 
    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CREATED_BY_PROBLEM_CASES_RN,
    )

    first_noted_date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        problem_case_events: Any
        id: int
        veterinary_center_id: int
        relapsed_from_case_id: int | None

    class Meta:
        ordering = ["-first_noted_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "veterinary_center",
                    "pet",
                    "problem_catalog",
                    "first_noted_date"
                ],
                name=UNIQUE_PROBLEM_CASE_PER_PET_PROBLEM_DATE_PER_CENTER
            )
        ]
        indexes = [
            models.Index(
                fields=["pet", "status"],
                name=IDX_PROBLEM_CASE_PET_STATUS
            ),
            models.Index(
                fields=["veterinary_center", "pet"],
                name=IDX_PROBLEM_CASE_CENTER_PET
            ),
            models.Index(
                fields=["problem_catalog"],
                name=IDX_PROBLEM_CASE_CATALOG
            ),
            models.Index(
                fields=["relapsed_from_case"],
                name=IDX_PROBLEM_CASE_RELAPSE
            ),
            models.Index(
                fields=["pet", "first_noted_date"],
                name=IDX_PROBLEM_CASE_PET_FIRST_NOTED
            ),
        ]

        
    def clean(self):
        if self.pet.veterinary_center_id != self.veterinary_center_id:
            raise ValidationError("Pet does not belong to veterinary_center")

        if self.problem_catalog.veterinary_center_id != self.veterinary_center_id:
            raise ValidationError("Problem catalog does not belong to veterinary_center")

        if self.relapsed_from_case is not None:
            if self.relapsed_from_case.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    "Relapsed case must belong to same veterinary_center"
                )

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.pet.name} — {self.problem_catalog.name}"
    

class Pet_Disease_Event(TrimFieldsMixin, models.Model):
    """
    Propósito: Eventos inmutables que construyen la historia del caso.
    """
    pet_disease_case = models.ForeignKey(
        PET_DISEASE_CASE_MODEL,
        on_delete=models.CASCADE,
        related_name=DISEASE_CASE_EVENTS_RN
    )
    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name=CONSULTATION_DISEASE_EVENTS_RN
    )
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_DISEASE_EVENTS_RN
    )
    event_type = models.CharField(
        max_length=20,
        choices=Choices_DiseaseEventType.choices,
    )
    event_date = models.DateTimeField(default=timezone.now)
    severity = models.CharField(
        max_length=10,
        choices=Choices_SeverityLevel.choices,
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=UPDATED_BY_DISEASE_EVENTS_RN,
    )
    
    if TYPE_CHECKING:
        id: int

    class Meta:
        ordering = ["event_date", "id"]
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
                name=UNIQUE_DISEASE_EVENT_PER_CASE_TYPE_DATETIME_CONSULTATION,
            ),
        ]

    def clean(self):
        if self.pk:
            raise ValidationError("Disease events are immutable.")

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.pet_disease_case.pet.name} — "
            f"{self.event_type} "
            f"({self.event_date:%Y-%m-%d %H:%M})"
        )
        
class Clinical_Comorbidity(models.Model):
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_CLINICAL_COMORBIDITIES_RN
    )
    disease_cases = models.ManyToManyField(
        PET_DISEASE_CASE_MODEL,
        related_name=DISEASE_CASES_CLINICAL_COMORBIDITIES_rn
    )
    

    if TYPE_CHECKING:
        id: int
        pet_id: int

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["pet"],
                name=UNIQUE_COMORBIDITY_PER_PET
            )
        ]

    def clean(self):
        for disease_case in self.disease_cases.all():
            if disease_case.pet_id != self.pet_id:
                raise ValidationError(
                    "All disease cases must belong to the same pet."
                )
                
    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)


class Pet_Problem_Event(TrimFieldsMixin, models.Model):
    """
    Propósito: Eventos inmutables asociados al problema (aparición, resolución, recaída).
    """
    pet_problem_case = models.ForeignKey(
        PET_PROBLEM_CASE_MODEL,
        on_delete=models.CASCADE,
        related_name=PROBLEM_CASE_PROBLEM_EVENTS_RN,
    )

    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=CONSULTATION_PROBLEM_EVENTS_RN,
    )
    
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_PROBLEM_EVENTS_RN
    )

    event_type = models.CharField(
        max_length=20,
        choices=Choices_ProblemEventType.choices,
    )

    event_date = models.DateTimeField(default=timezone.now)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    updated_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=UPDATED_BY_PROBLEM_EVENTS_RN,
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        consultation_id: int | None
        pet_problem_case_id: int

    class Meta:
        ordering = ["-event_date", "-id"]
        indexes = [
            models.Index(
                fields=["pet_problem_case", "-event_date", "-id"],
                name=IDX_PROBLEM_EVENT_CASE_DATE_ID
            ),
            models.Index(
                fields=["veterinary_center", "-event_date"],
                name=IDX_PROBLEM_EVENT_CENTER_DATE
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "pet_problem_case",
                    "event_type",
                    "event_date"
                ],
                name=UNIQUE_PROBLEM_EVENT_PER_CASE_TYPE_DATE
            )
        ]

    def clean(self):
        # Inmutabilidad
        if self.pk:
            raise ValidationError(
                "Problem events are immutable. Create a new event instead."
            )

        # Multi-tenant integrity
        if self.pet_problem_case.veterinary_center_id != self.veterinary_center_id:
            raise ValidationError(
                "Pet problem case does not belong to veterinary_center"
            )

        consultation = self.consultation

        if consultation is not None:
            if consultation.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    "Consultation does not belong to veterinary_center"
                )

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.pet_problem_case} — "
            f"{self.event_type} "
            f"({self.event_date:%Y-%m-%d %H:%M})"
        )
        
class Critical_Case(models.Model):
    """
    Propósito: Marca estados críticos activos de un paciente.
    Estado clínico derivado de una condición o evento.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CRITICAL_CASES_RN,
    )
    pet = models.ForeignKey(
        PET_MODEL,
        on_delete=models.CASCADE,
        related_name=PET_CRITICAL_CASES_RN,
    )
    disease_case = models.ForeignKey(
        PET_DISEASE_CASE_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=DISEASE_CASE_CRITICAL_CASES_RN,
    )
    problem_case = models.ForeignKey(
        PET_PROBLEM_CASE_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=PROBLEM_CASE_CRITICAL_CASES_RN,
    )
    consultation = models.ForeignKey(
        CONSULTATION_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CONSULTATION_CRITICAL_CASES_RN,
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Choices_CriticalCaseStatus.choices,
        default=Choices_CriticalCaseStatus.ACTIVE,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name=CREATED_BY_CRITICAL_CASES_RN,
    )
    
    if TYPE_CHECKING:
        veterinary_center_id: int

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    disease_case__isnull=False,
                    problem_case__isnull=True,
                    consultation__isnull=True,
                ) |
                models.Q(
                    disease_case__isnull=True,
                    problem_case__isnull=False,
                    consultation__isnull=True,
                ) |
                models.Q(
                    disease_case__isnull=True,
                    problem_case__isnull=True,
                    consultation__isnull=False,
                ),
                name=CRITICAL_CASE_SINGLE_ORIGIN,
            ),
            models.UniqueConstraint(
                fields=["disease_case"],
                condition=models.Q(status=Choices_CriticalCaseStatus.ACTIVE),
                name=UNIQUE_ACTIVE_CRITICAL_CASE_PER_DISEASE_CASE
            ),
            models.UniqueConstraint(
                fields=["problem_case"],
                condition=models.Q(status=Choices_CriticalCaseStatus.ACTIVE),
                name=UNIQUE_ACTIVE_CRITICAL_CASE_PER_PROBLEM_CASE
            ),
            models.UniqueConstraint(
                fields=["consultation"],
                condition=models.Q(status=Choices_CriticalCaseStatus.ACTIVE),
                name=UNIQUE_ACTIVE_CRITICAL_CASE_PER_CONSULTATION
            ),
        ]

        indexes = [
            models.Index(fields=["status"], name=IDX_CRITICAL_STATUS),
            models.Index(fields=["pet", "status"], name=IDX_CRITICAL_PET_STATUS),
            models.Index(fields=["veterinary_center", "status"], name=IDX_CRITICAL_CENTER_STATUS),
        ]

    def clean(self):
        if self.pet and self.veterinary_center_id != self.pet.veterinary_center_id:
            raise ValidationError(
                "veterinary_center must match pet.veterinary_center"
            )
        if self.status == cast(str, Choices_CriticalCaseStatus.ACTIVE) and self.resolved_at:
            raise ValidationError("resolved_at must be null while ACTIVE")

        if self.status == cast(str, Choices_CriticalCaseStatus.RESOLVED) and not self.resolved_at:
            raise ValidationError("resolved_at required when RESOLVED")

    def save(self, *args: Any, **kwargs: Any):
        if self.status == cast(str, Choices_CriticalCaseStatus.RESOLVED) and not self.resolved_at:
            self.resolved_at = timezone.now()

        if self.status == cast(str, Choices_CriticalCaseStatus.ACTIVE):
            self.resolved_at = None

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.status == cast(str, Choices_CriticalCaseStatus.ACTIVE)
    
__all__ = [
    "Pet", 
    "Pet_Disease_Case", 
    "Pet_Problem_Case", 
    "Pet_Disease_Event", 
    "Clinical_Comorbidity", 
    "Pet_Problem_Event",
    "Critical_Case",
]
