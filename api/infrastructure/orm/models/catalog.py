# api/infrastructure/orm/models/catalog.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import models

from api.shared.choices.choices import (
    Choices_Age_Focus_Types,
    Choices_Procedure_Category,
    Choices_SOAP_Context_Types,
)
from api.shared.constants.constants import (
    AZUL_CIELO,
    CENTER_CLINICAL_FOCUS_FOR_SOAP_TEMPLATES_RN,
    CENTER_CONSULTATION_TEMPLATES_RN,
    CENTER_CONSULTATION_TYPES_RN,
    CENTER_DISEASE_CATALOGS_RN,
    CENTER_DISEASE_GROUPS_RN,
    CENTER_FOLLOW_UP_CATEGORIES_RN,
    CENTER_MEDICATIONS_RN,
    CENTER_PROBLEM_CATALOGS_RN,
    CENTER_PROBLEM_GROUPS_RN,
    CENTER_PROCEDURE_TEMPLATES_RN,
    CENTER_PROCEDURE_TYPES_RN,
    CENTER_SOAP_TEMPLATES_RN,
    CENTER_SPECIES_IN_CENTER_RN,
    CENTER_VACCINE_TYPES_RN,
    CLINICAL_FOCUS_FOR_SOAP_TEMPLATE_MODEL,
    CONSULTATION_TYPE_CONSULTATION_TEMPLATES_RN,
    CONSULTATION_TYPE_MODEL,
    DEFAULT_SOAP_TEMPLATE_CONSULTATION_TEMPLATES_RN,
    DISEASE_GROUP_CATALOGS_RN,
    DISEASE_GROUP_MODEL,
    GLOBAL_BREED_BREEDS_IN_CENTER_RN,
    GLOBAL_BREED_MODEL,
    GLOBAL_SPECIES_MODEL,
    GLOBAL_SPECIES_SPECIES_IN_CENTER_RN,
    IDX_CONSULTATION_TEMPLATE_CENTER_ACTIVE_NAME,
    IDX_CONSULTATION_TEMPLATE_TYPE,
    IDX_CONSULTATION_TYPE_CENTER_CODE,
    IDX_CONSULTATION_TYPE_CENTER_LABEL,
    IDX_FOLLOW_UP_CATEGORY_CENTER_LABEL,
    IDX_MEDICATION_CENTER,
    IDX_PROBLEM_GROUP_CENTER_CODE,
    IDX_PROBLEM_GROUP_CENTER_NAME,
    IDX_PROBLEM_GROUP_CENTER_ORDER_NAME,
    IDX_PROCEDURE_TEMPLATE_CENTER_ACTIVE_NAME,
    IDX_PROCEDURE_TEMPLATE_TYPE,
    PROBLEM_GROUP_CATALOGS_RN,
    PROBLEM_GROUP_MODEL,
    PROCEDURE_TYPE_MODEL,
    PROCEDURE_TYPE_TEMPLATES_RN,
    SOAP_TEMPLATE_MODEL,
    SPECIES_DISEASE_GROUPS_RN,
    SPECIES_GLOBAL_BREEDS_RN,
    SPECIES_IN_CENTER_BREEDS_IN_CENTER_RN,
    SPECIES_IN_CENTER_MODEL,
    SPECIES_PROBLEM_CATALOGS_RN,
    SPECIES_PROBLEM_GROUPS_RN,
    SPECIES_SOAP_TEMPLATES_RN,
    SPECIES_VACCINE_TYPES_RN,
    UNIQUE_CLINICAL_FOCUS_PER_CENTER,
    UNIQUE_CONSULTATION_TEMPLATE_PER_CENTER,
    UNIQUE_CONSULTATION_TYPE_LABEL_PER_CENTER,
    UNIQUE_CONSULTATION_TYPE_PER_CENTER,
    UNIQUE_DISEASE_CODE_PER_CENTER,
    UNIQUE_DISEASE_GROUP_CODE_PER_CENTER,
    UNIQUE_DISEASE_GROUP_NAME_PER_CENTER,
    UNIQUE_DISEASE_NAME_SPECIES_CENTER,
    UNIQUE_FOLLOW_UP_CATEGORY_CODE_PER_CENTER,
    UNIQUE_GLOBAL_BREED_PER_GLOBAL_SPECIES,
    UNIQUE_GLOBAL_BREED_PER_SPECIES_IN_CENTER,
    UNIQUE_GLOBAL_SPECIES_PER_CENTER,
    UNIQUE_MEDICATION_CODE_PER_CENTER,
    UNIQUE_MEDICATION_PER_CENTER,
    UNIQUE_PROBLEM_CODE_PER_CENTER,
    UNIQUE_PROBLEM_GROUP_CODE_PER_CENTER,
    UNIQUE_PROBLEM_GROUP_NAME_PER_CENTER,
    UNIQUE_PROBLEM_NAME_PER_CENTER,
    UNIQUE_PROCEDURE_TEMPLATE_PER_CENTER,
    UNIQUE_PROCEDURE_TYPE_CODE_PER_CENTER,
    UNIQUE_PROCEDURE_TYPE_NAME_PER_CENTER,
    UNIQUE_SOAP_TEMPLATE_PER_CENTER,
    UNIQUE_VACCINE_CODE_PER_CENTER,
    UNIQUE_VACCINE_PER_SPECIES_CENTER,
    VERDE_ESMERALDA,
    VETERINARY_CENTER_MODEL,
    CENTER_STAFF_MEMBER_MODEL,
)
from api.shared.orm.audit_mixins import SoftDeleteAuditValidationMixin
from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin


# Models in api/infrastructure/orm/models/catalog.py:
# - Global_Species
# - Global_Breed
# - Species_In_Center
# - Breed_In_Center
# - Disease_Group
# - Disease_Catalog
# - Problem_Group
# - Problem_Catalog
# - Consultation_Type
# - Procedure_Type
# - Vaccine_Type
# - Medication
# - Follow_Up_Category
# - Clinical_Focus_For_SOAP_Template
# - SOAP_Template
# - Consultation_Template
# - Procedure_Template


def _normalize_required_code(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def _normalize_optional_code(value: Any) -> str | None:
    if value is None:
        return None

    cleaned_value = str(value).strip().upper()

    if cleaned_value == "":
        return None

    return cleaned_value


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


def _get_instance_center_id(
    *,
    instance: models.Model,
) -> int | None:
    veterinary_center_id = getattr(instance, "veterinary_center_id", None)

    if veterinary_center_id is not None:
        return int(veterinary_center_id)

    species_in_center_id = getattr(instance, "species_in_center_id", None)

    if species_in_center_id is not None:
        species_in_center = _get_related_object(
            instance=instance,
            related_field_name="species_in_center",
        )

        species_center_id = getattr(
            species_in_center,
            "veterinary_center_id",
            None,
        )

        if species_center_id is not None:
            return int(species_center_id)

    return None


def _validate_actor_fields_belong_to_center(
    *,
    instance: models.Model,
    errors: dict[str, list[str]],
) -> None:
    """
    Validates actor convenience/state fields.

    Detailed audit history belongs in Audit_Log.
    These fields remain only for direct current-row access.
    """

    center_id = _get_instance_center_id(instance=instance)

    if center_id is None:
        return

    for actor_field_name in (
        "created_by",
        "soft_deleted_by",
    ):
        actor_id = getattr(instance, f"{actor_field_name}_id", None)

        if actor_id is None:
            continue

        actor = _get_related_object(
            instance=instance,
            related_field_name=actor_field_name,
        )

        actor_center_id = getattr(actor, "veterinary_center_id", None)

        if actor_center_id is None:
            continue

        if int(actor_center_id) != center_id:
            _add_error(
                errors,
                actor_field_name,
                (
                    f"{actor_field_name} must belong to the same veterinary "
                    "center as this record."
                ),
            )


class Global_Species(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito: Catálogo maestro global de especies.
    No depende de ningún centro veterinario.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Global Species"
        verbose_name_plural = "Global Species"

    def __str__(self) -> str:
        return self.name


class Global_Breed(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito: Catálogo maestro global de razas.
    Cada raza pertenece a una especie global.
    """

    name = models.CharField(
        max_length=100,
    )

    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.PROTECT,
        related_name=SPECIES_GLOBAL_BREEDS_RN,
    )

    class Meta:
        ordering = ["species__name", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["species", "name"],
                name=UNIQUE_GLOBAL_BREED_PER_GLOBAL_SPECIES,
            ),
        ]

        indexes = [
            models.Index(fields=["species", "name"]),
        ]

        verbose_name = "Global Breed"
        verbose_name_plural = "Global Breeds"

    def __str__(self) -> str:
        return f"{self.name} ({self.species.name})"


class Species_In_Center(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito: Indica qué especies globales están habilitadas
    para un centro veterinario.

    No duplica el nombre.
    El nombre se obtiene desde global_species.

    Audit policy:
    - created_at / updated_at stay on the row.
    - created_by stays as convenience metadata.
    - detailed history belongs in Audit_Log.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_SPECIES_IN_CENTER_RN,
    )

    global_species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.PROTECT,
        related_name=GLOBAL_SPECIES_SPECIES_IN_CENTER_RN,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        global_species_id: int
        created_by_id: int | None

    class Meta:
        ordering = ["veterinary_center_id", "global_species__name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "global_species"],
                name=UNIQUE_GLOBAL_SPECIES_PER_CENTER,
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

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"{self.global_species.name} - Center {self.veterinary_center_id}"


class Breed_In_Center(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito: Indica qué razas globales están habilitadas
    para una especie habilitada en un centro veterinario.

    No duplica el nombre.
    El nombre se obtiene desde global_breed.

    Audit policy:
    - created_at / updated_at stay on the row.
    - created_by stays as convenience metadata.
    - detailed history belongs in Audit_Log.
    """

    species_in_center = models.ForeignKey(
        SPECIES_IN_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=SPECIES_IN_CENTER_BREEDS_IN_CENTER_RN,
    )

    global_breed = models.ForeignKey(
        GLOBAL_BREED_MODEL,
        on_delete=models.PROTECT,
        related_name=GLOBAL_BREED_BREEDS_IN_CENTER_RN,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        species_in_center_id: int
        global_breed_id: int
        created_by_id: int | None

    class Meta:
        ordering = [
            "species_in_center__global_species__name",
            "global_breed__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["species_in_center", "global_breed"],
                name=UNIQUE_GLOBAL_BREED_PER_SPECIES_IN_CENTER,
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

        errors: dict[str, list[str]] = {}

        if self.species_in_center_id and self.global_breed_id:
            species_global_species_id = self.species_in_center.global_species_id
            breed_global_species_id = self.global_breed.species_id

            if species_global_species_id != breed_global_species_id:
                _add_error(
                    errors,
                    "global_breed",
                    (
                        "The selected global breed does not belong to "
                        "the global species enabled in this center."
                    ),
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return (
            f"{self.global_breed.name} "
            f"({self.species_in_center.global_species.name}) - "
            f"Center {self.species_in_center.veterinary_center_id}"
        )


class Disease_Group(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Agrupación visual/funcional de enfermedades.

    Audit policy:
    - created_at / updated_at stay on the row.
    - created_by stays as convenience metadata.
    - soft_deleted_at / soft_deleted_by stay as current-row deletion state.
    - delete reason and before/after history belong in Audit_Log.
    """

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=20,
    )

    color = models.CharField(
        max_length=20,
        default=AZUL_CIELO,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_DISEASE_GROUPS_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_DISEASE_GROUPS_RN,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        ordering = ["order", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["name", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_DISEASE_GROUP_NAME_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_DISEASE_GROUP_CODE_PER_CENTER,
            ),
        ]

        indexes = [
            models.Index(fields=["veterinary_center", "order"]),
            models.Index(fields=["veterinary_center", "name"]),
            models.Index(fields=["veterinary_center", "code"]),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del grupo de enfermedades es obligatorio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.name


class Disease_Catalog(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Catálogo diagnóstico oficial del centro.

    Detailed audit history belongs in Audit_Log.
    """

    name = models.CharField(
        max_length=120,
    )

    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.PROTECT,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_DISEASE_CATALOGS_RN,
    )

    diagnostic_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )

    disease_group = models.ForeignKey(
        DISEASE_GROUP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=DISEASE_GROUP_CATALOGS_RN,
    )

    can_be_chronic = models.BooleanField(
        default=False,
    )

    contagious = models.BooleanField(
        default=False,
    )

    zoonotic = models.BooleanField(
        default=False,
        help_text="True if this disease can infect humans.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        species_id: int
        veterinary_center_id: int
        disease_group_id: int | None
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "species", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_DISEASE_NAME_SPECIES_CENTER,
            ),
            models.UniqueConstraint(
                fields=["diagnostic_code", "veterinary_center"],
                condition=(
                    models.Q(soft_deleted_at__isnull=True)
                    & models.Q(diagnostic_code__isnull=False)
                    & ~models.Q(diagnostic_code="")
                ),
                name=UNIQUE_DISEASE_CODE_PER_CENTER,
            ),
        ]

        indexes = [
            models.Index(fields=["veterinary_center", "name"]),
            models.Index(fields=["veterinary_center", "species"]),
            models.Index(fields=["veterinary_center", "diagnostic_code"]),
            models.Index(fields=["disease_group"]),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.diagnostic_code = _normalize_optional_code(self.diagnostic_code)

        if self.disease_group_id and self.veterinary_center_id:
            disease_group = self.disease_group

            if disease_group.veterinary_center_id != self.veterinary_center_id:
                _add_error(
                    errors,
                    "disease_group",
                    "El grupo de enfermedades pertenece a otro centro veterinario.",
                )

            if disease_group.soft_deleted_at is not None:
                _add_error(
                    errors,
                    "disease_group",
                    "No puede asociar una enfermedad a un grupo eliminado.",
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return f"{self.name} ({self.species.name})"


class Problem_Group(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Agrupación de motivos/síntomas, no diagnósticos.

    Detailed audit history belongs in Audit_Log.
    """

    name = models.CharField(
        max_length=100,
    )

    code = models.CharField(
        max_length=20,
    )

    color = models.CharField(
        max_length=20,
        default=VERDE_ESMERALDA,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_PROBLEM_GROUPS_RN,
    )

    order = models.PositiveIntegerField(
        default=0,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROBLEM_GROUPS_RN,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        ordering = ["order", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROBLEM_GROUP_NAME_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROBLEM_GROUP_CODE_PER_CENTER,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "order", "name"],
                name=IDX_PROBLEM_GROUP_CENTER_ORDER_NAME,
            ),
            models.Index(
                fields=["veterinary_center", "code"],
                name=IDX_PROBLEM_GROUP_CENTER_CODE,
            ),
            models.Index(
                fields=["veterinary_center", "name"],
                name=IDX_PROBLEM_GROUP_CENTER_NAME,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del grupo de problemas es obligatorio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.name


class Problem_Catalog(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Catálogo de problemas clínicos observables.

    Detailed audit history belongs in Audit_Log.
    """

    name = models.CharField(
        max_length=120,
    )

    code = models.CharField(
        max_length=30,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROBLEM_CATALOGS_RN,
    )

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_PROBLEM_CATALOGS_RN,
    )

    problem_group = models.ForeignKey(
        PROBLEM_GROUP_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=PROBLEM_GROUP_CATALOGS_RN,
    )

    is_emergency = models.BooleanField(
        default=False,
        help_text="True si típicamente es un problema potencialmente urgente.",
    )

    is_chronic_prone = models.BooleanField(
        default=False,
        help_text=(
            "True si suele asociarse a procesos crónicos "
            "(ej. cojera crónica, dolor crónico)."
        ),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        problem_group_id: int | None
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["name", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROBLEM_NAME_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROBLEM_CODE_PER_CENTER,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.name = str(self.name or "").strip()
        self.code = _normalize_required_code(self.code)

        if not self.name:
            _add_error(
                errors,
                "name",
                "El nombre del problema clínico es obligatorio.",
            )

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del problema clínico es obligatorio.",
            )

        if self.problem_group_id and self.veterinary_center_id:
            problem_group = self.problem_group

            if problem_group.veterinary_center_id != self.veterinary_center_id:
                _add_error(
                    errors,
                    "problem_group",
                    "El grupo de problemas pertenece a otro centro veterinario.",
                )

            if problem_group.soft_deleted_at is not None:
                _add_error(
                    errors,
                    "problem_group",
                    "No puede asociar un problema clínico a un grupo eliminado.",
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.name


class Consultation_Type(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Define qué tipo de consulta existe y cómo se comporta.

    Detailed audit history belongs in Audit_Log.
    """

    code = models.CharField(
        max_length=30,
        help_text="Stable code (general, clinical, vaccine, emergency, etc.)",
    )

    label = models.CharField(
        max_length=100,
        help_text="Display name (Consulta Clínica, Vacunación, etc.)",
    )

    color = models.CharField(
        max_length=20,
        default=AZUL_CIELO,
        help_text="Hex or Tailwind color for UI badges",
    )

    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio base de la consulta",
    )

    is_emergency = models.BooleanField(
        default=False,
        help_text="Marks this consultation as urgent",
    )

    is_preventive = models.BooleanField(
        default=False,
        help_text="Preventive / wellness consultation",
    )

    requires_follow_up = models.BooleanField(
        default=False,
        help_text="Usually requires a follow-up consultation",
    )

    age_focus = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        choices=Choices_Age_Focus_Types.choices,
        help_text="Optional age focus",
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CONSULTATION_TYPES_RN,
    )

    default_duration_minutes = models.PositiveIntegerField(
        default=30,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        constraints = [
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_CONSULTATION_TYPE_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["label", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_CONSULTATION_TYPE_LABEL_PER_CENTER,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "label"],
                name=IDX_CONSULTATION_TYPE_CENTER_LABEL,
            ),
            models.Index(
                fields=["veterinary_center", "code"],
                name=IDX_CONSULTATION_TYPE_CENTER_CODE,
            ),
        ]

        ordering = ["label"]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del tipo de consulta es obligatorio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.label


class Procedure_Type(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Catálogo de procedimientos clínicos.

    Detailed audit history belongs in Audit_Log.
    """

    code = models.CharField(
        max_length=30,
        blank=False,
        null=False,
    )

    name = models.CharField(
        max_length=100,
    )

    category = models.CharField(
        max_length=50,
        choices=Choices_Procedure_Category.choices,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROCEDURE_TYPES_RN,
    )

    requires_followup = models.BooleanField(
        default=False,
    )

    followup_interval_days = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    followup_interval_weeks = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    followup_interval_months = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    followup_interval_years = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROCEDURE_TYPE_CODE_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROCEDURE_TYPE_NAME_PER_CENTER,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del procedimiento es obligatorio.",
            )

        if self.requires_followup:
            if not any(
                [
                    self.followup_interval_days,
                    self.followup_interval_weeks,
                    self.followup_interval_months,
                    self.followup_interval_years,
                ]
            ):
                _add_error(
                    errors,
                    "requires_followup",
                    (
                        "Debe especificarse un intervalo de seguimiento "
                        "cuando requires_followup=True."
                    ),
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def get_followup_date(self, given_date: Any) -> Any | None:
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

    def __str__(self) -> str:
        return self.name


class Vaccine_Type(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Catálogo de vacunas y reglas de refuerzo.

    Detailed audit history belongs in Audit_Log.
    """

    code = models.CharField(
        max_length=30,
    )

    name = models.CharField(
        max_length=100,
    )

    species = models.ForeignKey(
        GLOBAL_SPECIES_MODEL,
        on_delete=models.PROTECT,
        related_name=SPECIES_VACCINE_TYPES_RN,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_VACCINE_TYPES_RN,
    )

    requires_booster = models.BooleanField(
        default=False,
    )

    booster_interval_days = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    booster_interval_weeks = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    booster_interval_months = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    booster_interval_years = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        species_id: int
        veterinary_center_id: int
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_VACCINE_CODE_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["name", "species", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_VACCINE_PER_SPECIES_CENTER,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código de la vacuna es obligatorio.",
            )

        if self.requires_booster:
            if not any(
                [
                    self.booster_interval_days,
                    self.booster_interval_weeks,
                    self.booster_interval_months,
                    self.booster_interval_years,
                ]
            ):
                _add_error(
                    errors,
                    "requires_booster",
                    (
                        "Debe especificarse un intervalo de refuerzo "
                        "cuando requires_booster=True."
                    ),
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def get_next_due_date(self, given_date: Any) -> Any | None:
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

    def __str__(self) -> str:
        return self.name


class Medication(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Catálogo de fármacos del centro.

    Detailed audit history belongs in Audit_Log.
    """

    code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=200,
    )

    concentration = models.CharField(
        max_length=100,
        blank=True,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_MEDICATIONS_RN,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_MEDICATION_CODE_PER_CENTER,
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "name", "concentration"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_MEDICATION_PER_CENTER,
            ),
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center"],
                name=IDX_MEDICATION_CENTER,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del medicamento es obligatorio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        if self.concentration:
            return f"{self.name} {self.concentration}"

        return self.name


class Follow_Up_Category(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Catálogo de categorías de seguimiento clínico.
    Define el tipo de acción de seguimiento requerida para un paciente.

    Detailed audit history belongs in Audit_Log.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_FOLLOW_UP_CATEGORIES_RN,
    )

    code = models.CharField(
        max_length=50,
    )

    label = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        ordering = ["label"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_FOLLOW_UP_CATEGORY_CODE_PER_CENTER,
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "label"],
                name=IDX_FOLLOW_UP_CATEGORY_CENTER_LABEL,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código de la categoría de seguimiento es obligatorio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.label


class Clinical_Focus_For_SOAP_Template(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Enfoque clínico (dermatología, cardio, etc.).

    Detailed audit history belongs in Audit_Log.
    """

    code = models.CharField(
        max_length=50,
        help_text="Stable machine-readable code (dermatology, gastro, etc.)",
    )

    label = models.CharField(
        max_length=100,
        help_text="Human readable label (example: Dermatología)",
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CLINICAL_FOCUS_FOR_SOAP_TEMPLATES_RN,
    )

    description = models.CharField(
        max_length=200,
        help_text="Descripción detallada del enfoque clínico",
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
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
        constraints = [
            models.UniqueConstraint(
                fields=["code", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_CLINICAL_FOCUS_PER_CENTER,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        self.code = _normalize_required_code(self.code)

        if not self.code:
            _add_error(
                errors,
                "code",
                "El código del enfoque clínico es obligatorio.",
            )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.label


class SOAP_Template(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Plantillas SOAP reutilizables.

    Detailed audit history belongs in Audit_Log.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_SOAP_TEMPLATES_RN,
    )

    name = models.CharField(
        max_length=200,
        help_text="Nombre identificable por el veterinario",
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

    context = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=Choices_SOAP_Context_Types.choices,
    )

    species = models.ManyToManyField(
        GLOBAL_SPECIES_MODEL,
        blank=True,
        related_name=SPECIES_SOAP_TEMPLATES_RN,
    )

    clinical_focus = models.ForeignKey(
        CLINICAL_FOCUS_FOR_SOAP_TEMPLATE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        clinical_focus_id: int | None
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["name", "veterinary_center"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_SOAP_TEMPLATE_PER_CENTER,
            )
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        if self.clinical_focus_id and self.veterinary_center_id:
            clinical_focus = self.clinical_focus

            if clinical_focus.veterinary_center_id != self.veterinary_center_id:
                _add_error(
                    errors,
                    "clinical_focus",
                    "El enfoque clínico pertenece a otro centro veterinario.",
                )

            if clinical_focus.soft_deleted_at is not None:
                _add_error(
                    errors,
                    "clinical_focus",
                    "No puede asociar una plantilla SOAP a un enfoque eliminado.",
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.name


class Consultation_Template(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Plantillas reutilizables para crear consultas clínicas.
    Define defaults operativos, clínicos y estructurales para nuevas consultas.

    Detailed audit history belongs in Audit_Log.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CONSULTATION_TEMPLATES_RN,
    )

    name = models.CharField(
        max_length=200,
        help_text="Nombre visible del template de consulta",
    )

    description = models.TextField(
        null=True,
        blank=True,
    )

    consultation_type = models.ForeignKey(
        CONSULTATION_TYPE_MODEL,
        on_delete=models.PROTECT,
        related_name=CONSULTATION_TYPE_CONSULTATION_TEMPLATES_RN,
        help_text="Tipo de consulta que define el flujo principal",
    )

    default_price = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Precio sugerido para esta consulta",
    )

    default_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duración estimada de la consulta",
    )

    default_soap_template = models.ForeignKey(
        SOAP_TEMPLATE_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name=DEFAULT_SOAP_TEMPLATE_CONSULTATION_TEMPLATES_RN,
        help_text="SOAP sugerido al crear la consulta",
    )

    is_emergency = models.BooleanField(
        default=False,
    )

    is_preventive = models.BooleanField(
        default=False,
    )

    requires_follow_up = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        consultation_type_id: int
        default_soap_template_id: int | None
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_CONSULTATION_TEMPLATE_PER_CENTER,
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active", "name"],
                name=IDX_CONSULTATION_TEMPLATE_CENTER_ACTIVE_NAME,
            ),
            models.Index(
                fields=["consultation_type"],
                name=IDX_CONSULTATION_TEMPLATE_TYPE,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        if self.consultation_type_id and self.veterinary_center_id:
            consultation_type = self.consultation_type

            if consultation_type.veterinary_center_id != self.veterinary_center_id:
                _add_error(
                    errors,
                    "consultation_type",
                    "El tipo de consulta pertenece a otro centro veterinario.",
                )

            if consultation_type.soft_deleted_at is not None:
                _add_error(
                    errors,
                    "consultation_type",
                    "No puede usar un tipo de consulta eliminado.",
                )

        if self.default_soap_template_id and self.veterinary_center_id:
            soap_template = self.default_soap_template

            if soap_template.veterinary_center_id != self.veterinary_center_id:
                _add_error(
                    errors,
                    "default_soap_template",
                    "La plantilla SOAP pertenece a otro centro veterinario.",
                )

            if soap_template.soft_deleted_at is not None:
                _add_error(
                    errors,
                    "default_soap_template",
                    "No puede usar una plantilla SOAP eliminada.",
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.name


class Procedure_Template(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito: Plantillas reutilizables para crear procedimientos clínicos.
    Define defaults operativos y clínicos para procedimientos frecuentes.

    Detailed audit history belongs in Audit_Log.
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_PROCEDURE_TEMPLATES_RN,
    )

    name = models.CharField(
        max_length=200,
    )

    procedure_type = models.ForeignKey(
        PROCEDURE_TYPE_MODEL,
        on_delete=models.PROTECT,
        related_name=PROCEDURE_TYPE_TEMPLATES_RN,
    )

    default_notes = models.TextField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        CENTER_STAFF_MEMBER_MODEL,
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
        CENTER_STAFF_MEMBER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        procedure_type_id: int
        created_by_id: int | None
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "name"],
                condition=models.Q(soft_deleted_at__isnull=True),
                name=UNIQUE_PROCEDURE_TEMPLATE_PER_CENTER,
            )
        ]

        indexes = [
            models.Index(
                fields=["veterinary_center", "is_active", "name"],
                name=IDX_PROCEDURE_TEMPLATE_CENTER_ACTIVE_NAME,
            ),
            models.Index(
                fields=["procedure_type"],
                name=IDX_PROCEDURE_TEMPLATE_TYPE,
            ),
        ]

    def clean(self) -> None:
        super().clean()

        errors: dict[str, list[str]] = {}

        if self.procedure_type_id and self.veterinary_center_id:
            procedure_type = self.procedure_type

            if procedure_type.veterinary_center_id != self.veterinary_center_id:
                _add_error(
                    errors,
                    "procedure_type",
                    "El tipo de procedimiento pertenece a otro centro veterinario.",
                )

            if procedure_type.soft_deleted_at is not None:
                _add_error(
                    errors,
                    "procedure_type",
                    "No puede usar un tipo de procedimiento eliminado.",
                )

        _validate_actor_fields_belong_to_center(
            instance=self,
            errors=errors,
        )

        _raise_errors(errors)

    def __str__(self) -> str:
        return self.name


__all__ = [
    "Global_Species",
    "Global_Breed",
    "Species_In_Center",
    "Breed_In_Center",
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