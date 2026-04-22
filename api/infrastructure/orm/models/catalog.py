# api/infrastructure/orm/models/catalog.py

from typing import Any
from django.db import models
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from typing import TYPE_CHECKING

from api.shared.choices.choices import (
    Choices_AgeFocusTypes,
    Choices_ProcedureCategory,
    Choices_SOAPContextTypes,
)

from api.shared.constants.constants import *

from api.shared.http.mixins import TrimFieldsMixin

# Models in api/infrastructure/orm/models/catalog.py:
# Generic_Species, Generic_Breeds, Species, Breed, Disease_Group, Disease_Catalog, Problem_Group, 
# Problem_Catalog, Consultation_Type, # Procedure_Type, Vaccine_Type, Medication, Follow_Up_Category, 
# Clinical_Focus_For_SOAP_Template, # SOAP_Template, Consultation_Template, Procedure_Template, 

class Global_Species(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo maestro global de especies.
    No depende de ningún centro veterinario.
    """
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Global Species"
        verbose_name_plural = "Global Species"

    def __str__(self) -> str:
        return self.name


class Global_Breed(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo maestro global de razas.
    Cada raza pertenece a una especie global.
    """
    name = models.CharField(max_length=100)

    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.CASCADE,
        related_name=SPECIES_GLOBAL_BREEDS_RN,
    )

    class Meta:
        ordering = ["species__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["species", "name"],
                name="unique_global_breed_per_global_species",
            ),
        ]
        indexes = [
            models.Index(fields=["species", "name"]),
        ]
        verbose_name = "Global Breed"
        verbose_name_plural = "Global Breeds"

    def __str__(self) -> str:
        return f"{self.name} ({self.species.name})"


class Species_In_Center(TrimFieldsMixin, models.Model):
    """
    Propósito: Indica qué especies globales están habilitadas
    para un centro veterinario.

    No duplica el nombre.
    El nombre se obtiene desde global_species.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_SPECIES_IN_CENTER_RN,
    )

    global_species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.CASCADE,
        related_name=GLOBAL_SPECIES_SPECIES_IN_CENTER_RN,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        veterinary_center_id: int
        global_species_id: int

    class Meta:
        ordering = ["veterinary_center_id", "global_species__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "global_species"],
                name="unique_global_species_per_center",
            ),
        ]
        indexes = [
            models.Index(fields=["veterinary_center", "global_species"]),
            models.Index(fields=["veterinary_center", "is_active"]),
        ]
        verbose_name = "Species In Center"
        verbose_name_plural = "Species In Center"

    @property
    def name(self) -> str:
        return self.global_species.name

    def __str__(self) -> str:
        return f"{self.global_species.name} - Center {self.veterinary_center_id}"


class Breed_In_Center(TrimFieldsMixin, models.Model):
    """
    Propósito: Indica qué razas globales están habilitadas
    para una especie habilitada en un centro veterinario.

    No duplica el nombre.
    El nombre se obtiene desde global_breed.
    """

    species_in_center = models.ForeignKey(
        SPECIES_IN_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=SPECIES_IN_CENTER_BREEDS_IN_CENTER_RN,
    )

    global_breed = models.ForeignKey(
        GLOBAL_BREED_MODEL,
        on_delete=models.CASCADE,
        related_name=GLOBAL_BREED_BREEDS_IN_CENTER_RN, 
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        species_in_center_id: int
        global_breed_id: int

    class Meta:
        ordering = [
            "species_in_center__global_species__name",
            "global_breed__name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["species_in_center", "global_breed"],
                name="unique_global_breed_per_species_in_center",
            ),
        ]
        indexes = [
            models.Index(fields=["species_in_center", "global_breed"]),
            models.Index(fields=["species_in_center", "is_active"]),
        ]
        verbose_name = "Breed In Center"
        verbose_name_plural = "Breeds In Center"

    @property
    def name(self) -> str:
        return self.global_breed.name

    def clean(self) -> None:
        super().clean()

        if not self.species_in_center_id or not self.global_breed_id:
            return

        species_global_species_id = self.species_in_center.global_species_id
        breed_global_species_id = self.global_breed.species_id

        if species_global_species_id != breed_global_species_id:
            raise ValidationError(
                {
                    "global_breed": (
                        "The selected global breed does not belong to "
                        "the global species enabled in this center."
                    )
                }
            )

    def __str__(self) -> str:
        return (
            f"{self.global_breed.name} "
            f"({self.species_in_center.global_species.name}) - "
            f"Center {self.species_in_center.veterinary_center_id}"
        )

class Disease_Group(TrimFieldsMixin, models.Model):
    """
    Propósito: Agrupación visual/funcional de enfermedades.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    color = models.CharField(max_length=20, default=AZUL_CIELO)

    description = models.TextField(blank=True, null=True)
    
    order = models.PositiveIntegerField(default=0)

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_DISEASE_GROUPS_RN
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_DISEASE_GROUPS_RN
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "veterinary_center"],
                name=UNIQUE_DISEASE_GROUP_NAME_PER_CENTER
            ),
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                name=UNIQUE_DISEASE_GROUP_CODE_PER_CENTER
            ),
        ]
        indexes = [
            models.Index(fields=["veterinary_center", "order"]),
            models.Index(fields=["veterinary_center", "name"]),
            models.Index(fields=["veterinary_center", "code"]),
        ]

    def __str__(self):
        return self.name

class Disease_Catalog(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo diagnóstico oficial del centro.
    """
    name = models.CharField(max_length=120)

    species = models.ForeignKey(GLOBAL_SPECIES_MODEL, on_delete=models.PROTECT)

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_DISEASE_CATALOGS_RN
    )

    diagnostic_code = models.CharField(max_length=50, blank=True, null=True)

    disease_group = models.ForeignKey(
        DISEASE_GROUP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=DISEASE_GROUP_CATALOGS_RN
    )

    can_be_chronic = models.BooleanField(default=False)
    contagious = models.BooleanField(default=False)
    zoonotic = models.BooleanField(
        default=False,
        help_text="True if this disease can infect humans."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "species", "veterinary_center"],
                name=UNIQUE_DISEASE_NAME_SPECIES_CENTER
            ),
            models.UniqueConstraint(
                fields=["diagnostic_code", "veterinary_center"],
                condition=models.Q(diagnostic_code__isnull=False),
                name=UNIQUE_DISEASE_CODE_PER_CENTER
            ),
        ]
        indexes = [
            models.Index(fields=["veterinary_center", "name"]),
            models.Index(fields=["veterinary_center", "species"]),
            models.Index(fields=["veterinary_center", "diagnostic_code"]),
            models.Index(fields=["disease_group"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.species.name})"
    
class Problem_Group(TrimFieldsMixin, models.Model):
    """
    Propósito: Agrupación de motivos/síntomas, no diagnósticos.
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    color = models.CharField(max_length=20, default=VERDE_ESMERALDA)

    description = models.TextField(blank=True, null=True)

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_PROBLEM_GROUPS_RN
    )

    order = models.PositiveIntegerField(default=0)

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROBLEM_GROUPS_RN
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                name=UNIQUE_PROBLEM_GROUP_NAME_PER_CENTER
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                name=UNIQUE_PROBLEM_GROUP_CODE_PER_CENTER
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "order", "name"],
                name=IDX_PROBLEM_GROUP_CENTER_ORDER_NAME
            ),
            models.Index(
                fields=["veterinary_center", "code"],
                name=IDX_PROBLEM_GROUP_CENTER_CODE
            ),
            models.Index(
                fields=["veterinary_center", "name"],
                name=IDX_PROBLEM_GROUP_CENTER_NAME
            ),
        ]

    def __str__(self):
        return self.name

class Problem_Catalog(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo de problemas clínicos observables.
    """
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30)

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROBLEM_CATALOGS_RN
    )

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_PROBLEM_CATALOGS_RN
    )

    problem_group = models.ForeignKey(
        PROBLEM_GROUP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=PROBLEM_GROUP_CATALOGS_RN
    )

    is_emergency = models.BooleanField(
        default=False,
        help_text="True si típicamente es un problema potencialmente urgente."
    )

    is_chronic_prone = models.BooleanField(
        default=False,
        help_text="True si suele asociarse a procesos crónicos (ej. cojera crónica, dolor crónico)."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "veterinary_center"],
                name=UNIQUE_PROBLEM_PER_CENTER
            )
        ]

    def __str__(self):
        return self.name
    
class Consultation_Type(TrimFieldsMixin, models.Model):
    """
    Propósito: Define qué tipo de consulta existe y cómo se comporta.
    If it's name is changed, change Pet also
    """
    code = models.CharField(
        max_length=30,
        help_text="Stable code (general, clinical, vaccine, emergency, etc.)"
    )

    # Human-readable label
    label = models.CharField(
        max_length=100,
        help_text="Display name (Consulta Clínica, Vacunación, etc.)"
    )

    # UI hint (same pattern as Disease_Group / Problem_Group)
    color = models.CharField(
        max_length=20,
        default=AZUL_CIELO,
        help_text="Hex or Tailwind color for UI badges"
    )

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio base de la consulta"
    )

    is_emergency = models.BooleanField(
        default=False,
        help_text="Marks this consultation as urgent"
    )

    is_preventive = models.BooleanField(
        default=False,
        help_text="Preventive / wellness consultation"
    )

    requires_follow_up = models.BooleanField(
        default=False,
        help_text="Usually requires a follow-up consultation"
    )

    age_focus = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=Choices_AgeFocusTypes.choices,
        help_text="Optional age focus"
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CONSULTATION_TYPES_RN
    )

    default_duration_minutes = models.PositiveIntegerField(default=30)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                name="unique_consultation_type_per_center"
            ),
            models.UniqueConstraint(
                fields=["label", "veterinary_center"],
                name="unique_consultation_type_label_per_center"
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "label"],
                name=IDX_CONSULTATION_TYPE_CENTER_LABEL
            ),
            models.Index(
                fields=["veterinary_center", "code"],
                name=IDX_COSULTATION_TYPE_CENTER_CODE
            ),
        ]

        ordering = ["label"]

        
    def save(self, *args: Any, **kwargs: Any):
        if self.code:
            self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.label
    
class Procedure_Type(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo de procedimientos clínicos.
    """

    code = models.CharField(max_length=30, blank=False, null=False,)

    name = models.CharField(max_length=100)

    category = models.CharField(
        max_length=50,
        choices=Choices_ProcedureCategory.choices
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROCEDURE_TYPES_RN
    )

    requires_followup = models.BooleanField(default=False)

    followup_interval_days = models.PositiveIntegerField(blank=True, null=True)
    followup_interval_weeks = models.PositiveIntegerField(blank=True, null=True)
    followup_interval_months = models.PositiveIntegerField(blank=True, null=True)
    followup_interval_years = models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                name=UNIQUE_PROCEDURE_TYPE_CODE_PER_CENTER
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                name=UNIQUE_PROCEDURE_TYPE_NAME_PER_CENTER
            ),
        ]


    def save(self, *args: Any, **kwargs: Any):
        if not self.code:
            raise ValueError("Procedure_Type.code cannot be empty")
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def get_followup_date(self, given_date: Any):
        if not self.requires_followup:
            return None

        delta = relativedelta(
            days=self.followup_interval_days or 0,
            weeks=self.followup_interval_weeks or 0,
            months=self.followup_interval_months or 0,
            years=self.followup_interval_years or 0,
        )

        if delta == relativedelta():
            return None

        return given_date + delta

    def __str__(self):
        return self.name

class Vaccine_Type(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo de vacunas y reglas de refuerzo.
    """

    code = models.CharField(max_length=30)

    name = models.CharField(max_length=100)

    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.PROTECT,
        related_name=SPECIES_VACCINE_TYPES_RN
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_VACCINE_TYPES_RN
    )

    requires_booster = models.BooleanField(default=False)

    booster_interval_days = models.PositiveIntegerField(blank=True, null=True)
    booster_interval_weeks = models.PositiveIntegerField(blank=True, null=True)
    booster_interval_months = models.PositiveIntegerField(blank=True, null=True)
    booster_interval_years = models.PositiveIntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                name=UNIQUE_VACCINE_CODE_PER_CENTER
            ),
            models.UniqueConstraint(
                fields=["name", "species", "veterinary_center"],
                name=UNIQUE_VACCINE_PER_SPECIES_CENTER
            )
        ]

    def clean(self):
        if self.requires_booster:
            if not any([
                self.booster_interval_days,
                self.booster_interval_weeks,
                self.booster_interval_months,
                self.booster_interval_years,
            ]):
                raise ValidationError(
                    "Booster interval must be specified when requires_booster=True"
                )

    def save(self, *args: Any, **kwargs: Any):
        if self.code:
            self.code = self.code.strip().upper()
        if self.name:
            self.name = self.name.strip()
        self.full_clean()
        super().save(*args, **kwargs)

    def get_next_due_date(self, given_date: Any):
        if not self.requires_booster:
            return None

        delta = relativedelta(
            days=self.booster_interval_days or 0,
            weeks=self.booster_interval_weeks or 0,
            months=self.booster_interval_months or 0,
            years=self.booster_interval_years or 0,
        )

        if delta == relativedelta():
            return None

        return given_date + delta

    def __str__(self):
        return self.name
    
class Medication(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo de fármacos del centro.
    """

    code = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    concentration = models.CharField(max_length=100, blank=True)
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_MEDICATIONS_RN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                name=UNIQUE_MEDICATION_CODE_PER_CENTER
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "name", "concentration"],
                name=UNIQUE_MEDICATION_PER_CENTER
            )
        ]
        indexes = [
            models.Index(
                fields=["veterinary_center"],
                name=IDX_MEDICATION_CENTER
            )
        ]

    def save(self, *args: Any, **kwargs: Any):
        if self.code:
            self.code = self.code.strip().upper()

        if self.name:
            self.name = self.name.strip()

        if self.concentration:
            self.concentration = self.concentration.strip()

        super().save(*args, **kwargs)

    def __str__(self):
        if self.concentration:
            return f"{self.name} {self.concentration}"
        return self.name
    
class Follow_Up_Category(TrimFieldsMixin, models.Model):
    """
    Propósito: Catálogo de categorías de seguimiento clínico.
    Define el tipo de acción de seguimiento requerida para un paciente.
    Ej: control clínico, llamada telefónica, revisión postoperatoria, etc.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_FOLLOW_UP_CATEGORIES_RN
    )
    code = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                name=UNIQUE_FOLLOW_UP_CATEGORY_CODE_PER_CENTER
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "label"],
                name=IDX_FOLLOW_UP_CATEGORY_CENTER_LABEL
            )
        ]


    def save(self, *args: Any, **kwargs: Any):
        if self.code:
            self.code = self.code.strip().upper()

        if self.label:
            self.label = self.label.strip()

        super().save(*args, **kwargs)


    # examples of clinical_focuses:
    
    # general
    # emergency
    # preventive
    # dermatology
    # gastrointestinal
    # respiratory
    # cardiology
    # orthopedics
    # neurology
    # reproductive
    # endocrine
    # other
    
class Clinical_Focus_For_SOAP_Template(models.Model):
    """
    Propósito: Enfoque clínico (dermatología, cardio, etc.).
    """
    code = models.CharField(
        max_length=50,
        help_text="Stable machine-readable code (dermatology, gastro, etc.)"
    )
    label = models.CharField(
        max_length=100,
        help_text="Human readable label (example: Dermatología)"
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CLINICAL_FOCUS_FOR_SOAP_TEMPLATES_RN
    )
    
    description = models.CharField(
        max_length=200,
        help_text="Descripción detallada del enfoque clínico"
    )

    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                name="unique_clinical_focus_per_center"
            )
        ]

class SOAP_Template(TrimFieldsMixin, models.Model):
    """
    Propósito: Plantillas SOAP reutilizables.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_SOAP_TEMPLATES_RN
    )

    name = models.CharField(
        max_length=200,
        help_text="Nombre identificable por el veterinario"
    )

    subjective = models.TextField(blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    assessment = models.TextField(blank=True, null=True)
    plan = models.TextField(blank=True, null=True)

    # it is a match for consultation type
    context = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=Choices_SOAPContextTypes.choices
    )

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_SOAP_TEMPLATES_RN
    )

    clinical_focus = models.ForeignKey(
        CLINICAL_FOCUS_FOR_SOAP_TEMPLATE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "veterinary_center"],
                name="unique_soap_template_per_center"
            )
        ]

    def __str__(self):
        return self.name
    
class Consultation_Template(TrimFieldsMixin, models.Model):
    """
    Propósito: Plantillas reutilizables para crear consultas clínicas.
    Define defaults operativos, clínicos y estructurales para nuevas consultas.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_CONSULTATION_TEMPLATES_RN,
    )
    name = models.CharField(
        max_length=200,
        help_text="Nombre visible del template de consulta"
    )
    description = models.TextField(
        null=True,
        blank=True
    )
    consultation_type = models.ForeignKey(
        CONSULTATION_TYPE_MODEL,
        on_delete=models.PROTECT,
        related_name=CONSULTATION_TYPE_CONSULTATION_TEMPLATES_RN,
        help_text="Tipo de consulta que define el flujo principal"
    )
    default_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Precio sugerido para esta consulta"
    )
    default_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duración estimada de la consulta"
    )
    default_soap_template = models.ForeignKey(
        SOAP_TEMPLATE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=DEFAULT_SOAP_TEMPLATE_CONSULTATION_TEMPLATES_RN,
        help_text="SOAP sugerido al crear la consulta"
    )
    is_emergency = models.BooleanField(default=False)
    is_preventive = models.BooleanField(default=False)
    requires_follow_up = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                name=UNIQUE_CONSULTATION_TEMPLATE_PER_CENTER
            )
        ]
        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active", "name"],
                name=IDX_CONSULTATION_TEMPLATE_CENTER_ACTIVE_NAME
            ),
            models.Index(
                fields=["consultation_type"],
                name=IDX_CONSULTATION_TEMPLATE_TYPE
            ),
        ]

    def save(self, *args: Any, **kwargs: Any):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Procedure_Template(TrimFieldsMixin, models.Model):
    """
    Propósito: Plantillas reutilizables para crear procedimientos clínicos.
    Define defaults operativos y clínicos para procedimientos frecuentes.
    """
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.PROTECT,
        related_name=CENTER_PROCEDURE_TEMPLATES_RN
    )
    name = models.CharField(max_length=200)
    procedure_type = models.ForeignKey(
        PROCEDURE_TYPE_MODEL,
        on_delete=models.PROTECT,
        related_name=PROCEDURE_TYPE_TEMPLATES_RN
    )
    default_notes = models.TextField(
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                name=UNIQUE_PROCEDURE_TEMPLATE_PER_CENTER
            )
        ]
        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active", "name"],
                name=IDX_PROCEDURE_TEMPLATE_CENTER_ACTIVE_NAME
            ),
            models.Index(
                fields=["procedure_type"],
                name=IDX_PROCEDURE_TEMPLATE_TYPE
            ),
        ]

    def save(self, *args: Any, **kwargs: Any):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


__all__ = [
    "Global_Species",
    "Global_Breed",
    "Species_In_Center",
    "Disease_Group",
    "Disease_Catalog",
    "Problem_Group",
    "Problem_Catalog",
    "Consultation_Type",
    "Procedure_Type",
    "Vaccine_Type",
    "Medication",
    "Follow_Up_Category",
    "Clinical_Focus_For_SOAP_Template",
    "SOAP_Template",
    "Consultation_Template",
    "Procedure_Template",
]