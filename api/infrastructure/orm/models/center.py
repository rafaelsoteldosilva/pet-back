# api/infrastructure/orm/models/center.py

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from api.shared.choices.choices import (
    Choices_Center_Contact_Type,
    Choices_Diagnostic_Coding_System,
    Choices_Role,
)
from api.shared.constants.constants import (
    CENTER_CLINICAL_FOCUSES_RN,
    CENTER_CONTACTS_RN,
    CENTER_SETTINGS_RN,
    CLOUDINARY_PUBLIC_ID_MAX_LENGTH,
    CLOUDINARY_RESOURCE_TYPE_MAX_LENGTH,
    INTERNATIONAL_PHONE_NUMBER_REGEX,
    NAMES_MAX_LENGTH,
    PERSONNEL_LOGIN_SESSIONS_RN,
    SPECIES_IN_CENTER_MODEL,
    UNIQUE_CENTER_CONTACT_DOCUMENT_ID_PER_CENTER,
    URLS_MAX_LENGTH,
    VETERINARY_CENTER_MODEL,
    Center_Staff_Membership_MODEL,
    CENTER_CLINICAL_FOCUS_MODEL,
)
from api.shared.orm.audit_mixins import SoftDeleteAuditValidationMixin
from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin
from api.shared.utils.normalize_document_id import (
    is_valid_chilean_rut,
    normalize_document_id,
)


# Models located in api/infrastructure/orm/models/center.py:
# Veterinary_Center
# Veterinary_Center_Settings
# Center_Clinical_Focus
# Center_Staff_Membership
# Personnel_Login_Session
# Center_Contact
# Image


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _normalize_required_code(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().upper()


def _validate_and_normalize_chilean_document_id(value: Any) -> str:
    """
    Normalizes and validates a Chilean RUT/RUN document ID.

    Empty document_id is allowed for contacts, but not for personnel.
    Personnel validation enforces it later.
    """

    document_id = _clean_string(value)

    if not document_id:
        return ""

    normalized_document_id = normalize_document_id(document_id)

    if not normalized_document_id or not is_valid_chilean_rut(normalized_document_id):
        raise ValidationError(
            {
                "document_id": "El documento indicado no es un RUT chileno válido.",
            }
        )

    return normalized_document_id


class Veterinary_Center(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Entidad raíz del dominio Center.

    Todo vive dentro de un centro veterinario.
    Aísla datos, reglas, catálogos y operaciones por clínica.
    """

    name = models.CharField(
        max_length=120,
    )

    country_code = models.CharField(
        max_length=5,
    )

    email = models.EmailField()

    address = models.CharField(
        max_length=200,
    )

    phone = models.CharField(
        max_length=50,
    )

    clinic_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code used for history codes.",
    )

    diagnostic_code_system = models.CharField(
        max_length=20,
        choices=Choices_Diagnostic_Coding_System.choices,
        default=Choices_Diagnostic_Coding_System.INTERNAL,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Centro activo",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        id: int
        center_settings: "Veterinary_Center_Settings"
        follow_up_categories: Any

    class Meta:
        indexes = [
            models.Index(fields=["country_code"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self) -> None:
        super().clean()

        self.name = _clean_string(self.name)
        self.country_code = _clean_string(self.country_code).upper()
        self.email = _clean_string(self.email).lower()
        self.address = _clean_string(self.address)
        self.phone = _clean_string(self.phone)
        self.clinic_code = _clean_string(self.clinic_code).upper()

        if not self.name:
            raise ValidationError(
                {
                    "name": "El nombre del centro veterinario es obligatorio.",
                }
            )

        if not self.country_code:
            raise ValidationError(
                {
                    "country_code": "El país del centro veterinario es obligatorio.",
                }
            )

        if not self.email:
            raise ValidationError(
                {
                    "email": "El correo electrónico del centro es obligatorio.",
                }
            )

        if not self.clinic_code:
            raise ValidationError(
                {
                    "clinic_code": "El código del centro veterinario es obligatorio.",
                }
            )

    def __str__(self) -> str:
        return self.name


class Veterinary_Center_Settings(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Configuración global del centro veterinario.

    Para qué sirve:
    - Definir identidad visible del centro.
    - Configurar comportamiento del sistema.
    - Controlar especies permitidas.
    - Branding y UI.
    - Preferencias de recordatorios.
    """

    veterinary_center = models.OneToOneField(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_SETTINGS_RN,
    )

    name = models.CharField(
        max_length=150,
        verbose_name="Nombre comercial",
    )

    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?[\d\s\-]+$",
                message="Número de teléfono inválido.",
            )
        ],
        verbose_name="Teléfono",
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Correo electrónico",
    )

    address = models.CharField(
        max_length=255,
        verbose_name="Dirección",
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    country = models.CharField(
        max_length=100,
        default="Chile",
    )

    allowed_species = models.ManyToManyField(
        SPECIES_IN_CENTER_MODEL,
        blank=True,
        related_name="+",
        verbose_name="Especies permitidas",
    )

    default_consultation_duration = models.PositiveIntegerField(
        default=30,
        verbose_name="Duración consulta (minutos)",
    )

    allow_emergency_attention = models.BooleanField(
        default=True,
        verbose_name="Atiende urgencias",
    )

    require_microchip_for_surgery = models.BooleanField(
        default=True,
    )

    require_microchip_for_hospitalization = models.BooleanField(
        default=False,
    )

    require_microchip_for_consultation = models.BooleanField(
        default=False,
    )

    pet_history_code_prefix = models.CharField(
        max_length=10,
        default="PET",
        verbose_name="Prefijo ficha paciente",
    )

    auto_generate_history_code = models.BooleanField(
        default=True,
    )

    logo_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Logo del centro",
    )

    primary_color = models.CharField(
        max_length=7,
        default="#3b82f6",
        verbose_name="Color principal",
    )

    secondary_color = models.CharField(
        max_length=7,
        default="#10b981",
        verbose_name="Color secundario",
    )

    send_vaccine_reminders = models.BooleanField(
        default=True,
    )

    send_followup_reminders = models.BooleanField(
        default=True,
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

    class Meta:
        verbose_name = "Configuración del centro"
        verbose_name_plural = "Configuraciones de centros"

    def clean(self) -> None:
        super().clean()

        self.name = _clean_string(self.name)
        self.phone = _clean_string(self.phone)
        self.address = _clean_string(self.address)
        self.city = _clean_string(self.city) or None
        self.country = _clean_string(self.country)

        if self.email:
            self.email = _clean_string(self.email).lower()
        else:
            self.email = None

        self.pet_history_code_prefix = _clean_string(
            self.pet_history_code_prefix,
        ).upper()

        if self.logo_url:
            self.logo_url = _clean_string(self.logo_url)
        else:
            self.logo_url = None

        if not self.name:
            raise ValidationError(
                {
                    "name": "El nombre comercial del centro es obligatorio.",
                }
            )

        if not self.phone:
            raise ValidationError(
                {
                    "phone": "El teléfono del centro es obligatorio.",
                }
            )

        if not self.address:
            raise ValidationError(
                {
                    "address": "La dirección del centro es obligatoria.",
                }
            )

        if not self.country:
            raise ValidationError(
                {
                    "country": "El país del centro es obligatorio.",
                }
            )

        if not self.pet_history_code_prefix:
            raise ValidationError(
                {
                    "pet_history_code_prefix": (
                        "El prefijo de ficha clínica es obligatorio."
                    ),
                }
            )

    def __str__(self) -> str:
        return f"Settings - {self.name}"


class Center_Clinical_Focus(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Define un enfoque clínico profesional habilitado por centro.

    Ej:
    - Dermatología
    - Cirugía
    - Medicina Felina
    - Cardiología
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CLINICAL_FOCUSES_RN,
    )

    code = models.CharField(
        max_length=50,
        help_text="Stable machine-readable code.",
    )

    label = models.CharField(
        max_length=100,
        help_text="Human readable label.",
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional detailed explanation of this focus.",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    soft_deleted_by = models.ForeignKey(
        Center_Staff_Membership_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        soft_deleted_by_id: int | None

    class Meta:
        ordering = ["label"]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "code"],
                condition=Q(soft_deleted_at__isnull=True),
                name="unique_active_center_clinical_focus_code_per_center",
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "label"],
                condition=Q(soft_deleted_at__isnull=True),
                name="unique_active_center_clinical_focus_label_per_center",
            ),
        ]

        indexes = [
            models.Index(fields=["veterinary_center", "code"]),
            models.Index(fields=["veterinary_center", "label"]),
            models.Index(fields=["veterinary_center", "is_active"]),
            models.Index(fields=["veterinary_center", "soft_deleted_at"]),
            models.Index(fields=["veterinary_center", "is_active", "soft_deleted_at"]),
        ]

    def clean(self) -> None:
        super().clean()

        self.code = _normalize_required_code(self.code)
        self.label = _clean_string(self.label)

        if self.description:
            self.description = _clean_string(self.description)
        else:
            self.description = None

        if not self.code:
            raise ValidationError(
                {
                    "code": "El código del enfoque clínico es obligatorio.",
                }
            )

        if not self.label:
            raise ValidationError(
                {
                    "label": "La etiqueta del enfoque clínico es obligatoria.",
                }
            )

        if self.soft_deleted_at is not None:
            self.is_active = False

        if self.soft_deleted_by_id and self.veterinary_center_id:
            if self.soft_deleted_by.veterinary_center_id != self.veterinary_center_id:
                raise ValidationError(
                    {
                        "soft_deleted_by": (
                            "El usuario que elimina el enfoque clínico debe pertenecer "
                            "al mismo centro veterinario."
                        ),
                    }
                )

    def __str__(self) -> str:
        return self.label


class Center_Staff_Membership(TrimFieldsMixin, FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Representa la membresía laboral de un usuario global dentro de un centro veterinario.

    Importante:
    - El login pertenece a Pet_Control_User.
    - Este modelo dice en qué centro trabaja ese usuario.
    - El mismo usuario puede tener varios registros aquí, uno por centro.
    - El rol pertenece a la relación usuario-centro, no al usuario global.
    - Los datos laborales locales viven aquí.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="user_staff_memberships",
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name="center_staff_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Choices_Role.choices,
        db_index=True,
    )

    job_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    professional_license_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    work_email = models.EmailField(
        blank=True,
        null=True,
    )

    work_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    clinical_focuses = models.ManyToManyField(
        CENTER_CLINICAL_FOCUS_MODEL,
        related_name="+",
        blank=True,
    )

    if TYPE_CHECKING:
        id: int
        user_id: int | None
        veterinary_center_id: int | None
        personnel_login_sessions: Any

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["veterinary_center", "user"]),
            models.Index(fields=["veterinary_center", "role"]),
            models.Index(fields=["veterinary_center", "is_active"]),
            models.Index(fields=["veterinary_center", "work_email"]),
            models.Index(fields=["veterinary_center", "professional_license_number"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["veterinary_center", "user"],
                name="unique_vet_center_staff_membership_user_per_center",
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "work_email"],
                condition=(
                    Q(is_active=True)
                    & Q(work_email__isnull=False)
                ),
                name="unique_active_vet_center_staff_membership_work_email_per_center",
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "professional_license_number"],
                condition=(
                    Q(is_active=True)
                    & Q(professional_license_number__isnull=False)
                ),
                name="unique_active_vet_center_staff_membership_license_per_center",
            ),
        ]

    @property
    def full_name(self) -> str:
        return self.user.full_name

    @property
    def personal_email(self) -> str:
        return self.user.email

    @property
    def effective_email(self) -> str:
        return self.work_email or self.user.email

    @property
    def document_id(self) -> str:
        return self.user.document_id

    @property
    def country_code(self) -> str:
        return self.user.country_code

    @property
    def cell_phone(self) -> str:
        return self.user.cell_phone

    @property
    def is_currently_logged_in(self) -> bool:
        return self.personnel_login_sessions.filter(
            logout_at__isnull=True,
        ).exists()

    def clean(self) -> None:
        super().clean()

        user_id = cast(int | None, getattr(self, "user_id", None))
        veterinary_center_id = cast(
            int | None,
            getattr(self, "veterinary_center_id", None),
        )

        if user_id is None:
            raise ValidationError(
                {
                    "user": "El usuario asociado al personal es obligatorio.",
                }
            )

        if veterinary_center_id is None:
            raise ValidationError(
                {
                    "veterinary_center": (
                        "El centro veterinario asociado al personal es obligatorio."
                    ),
                }
            )

        if not getattr(self.user, "is_active", True):
            raise ValidationError(
                {
                    "user": "El usuario asociado está inactivo.",
                }
            )

        self.role = _clean_string(self.role)

        if self.job_title:
            self.job_title = _clean_string(self.job_title)
        else:
            self.job_title = None

        if self.professional_license_number:
            self.professional_license_number = _clean_string(
                self.professional_license_number,
            ).upper()
        else:
            self.professional_license_number = None

        if self.work_email:
            self.work_email = _clean_string(self.work_email).lower()
        else:
            self.work_email = None

        if self.work_phone:
            self.work_phone = _clean_string(self.work_phone)
        else:
            self.work_phone = None

        valid_roles = {choice[0] for choice in Choices_Role.choices}

        if self.role not in valid_roles:
            raise ValidationError(
                {
                    "role": "El rol indicado no es válido.",
                }
            )

    def __str__(self) -> str:
        return f"{self.full_name} — {self.veterinary_center} ({self.role})"


class Personnel_Login_Session(FullCleanOnSaveMixin, models.Model):
    """
    Propósito:
    Auditoría básica de sesiones de login.

    Este modelo conserva related_name porque el backend usa:
    personnel.personnel_login_sessions
    """

    personnel = models.ForeignKey(
        Center_Staff_Membership_MODEL,
        on_delete=models.CASCADE,
        related_name=PERSONNEL_LOGIN_SESSIONS_RN,
    )

    login_at = models.DateTimeField()

    logout_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-login_at"]

        indexes = [
            models.Index(fields=["personnel", "logout_at"]),
            models.Index(fields=["login_at"]),
        ]

    def __str__(self) -> str:
        logout_display = (
            self.logout_at.strftime("%Y-%m-%d %H:%M")
            if self.logout_at
            else "ACTIVE"
        )

        return f"{self.personnel.full_name} — {self.login_at} → {logout_display}"


class Center_Contact(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Persona o institución reutilizable dentro de un centro veterinario.

    No representa una relación con una mascota.
    Esa relación vive en Pet_Contact_Link.

    Borrado:
    - soft_deleted_at indica borrado lógico.
    - is_active indica disponibilidad operativa.
    - Al borrar lógicamente desde comandos, debes setear ambos:
      is_active=False y soft_deleted_at=timezone.now().
    """

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_CONTACTS_RN,
    )

    center_contact_type = models.CharField(
        max_length=20,
        choices=Choices_Center_Contact_Type.choices,
        default=Choices_Center_Contact_Type.PERSON.value,
        db_index=True,
        help_text="Define si el contacto es una persona natural o una institución.",
    )

    first_name = models.CharField(
        max_length=100,
        blank=True,
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
    )

    institution_name = models.CharField(
        max_length=150,
        blank=True,
    )

    document_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Documento de identidad, RUT, DNI, RIF u otro identificador.",
    )

    email = models.EmailField(
        max_length=254,
        blank=True,
    )

    primary_phone = models.CharField(
        max_length=30,
        blank=True,
        validators=[
            RegexValidator(INTERNATIONAL_PHONE_NUMBER_REGEX),
        ],
    )

    secondary_phone = models.CharField(
        max_length=30,
        blank=True,
        validators=[
            RegexValidator(INTERNATIONAL_PHONE_NUMBER_REGEX),
        ],
    )

    tertiary_phone = models.CharField(
        max_length=30,
        blank=True,
        validators=[
            RegexValidator(INTERNATIONAL_PHONE_NUMBER_REGEX),
        ],
    )

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    city = models.CharField(
        max_length=100,
        blank=True,
    )

    region = models.CharField(
        max_length=100,
        blank=True,
    )

    country = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    soft_deleted_by = models.ForeignKey(
        Center_Staff_Membership_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        soft_deleted_by_id: int | None

    class Meta:
        verbose_name = "Contacto"
        verbose_name_plural = "Contactos"

        ordering = [
            "last_name",
            "first_name",
            "institution_name",
        ]

        indexes = [
            models.Index(fields=["veterinary_center", "center_contact_type"]),
            models.Index(fields=["veterinary_center", "last_name", "first_name"]),
            models.Index(fields=["veterinary_center", "institution_name"]),
            models.Index(fields=["veterinary_center", "document_id"]),
            models.Index(fields=["veterinary_center", "is_active"]),
            models.Index(fields=["veterinary_center", "soft_deleted_at"]),
            models.Index(fields=["veterinary_center", "is_active", "soft_deleted_at"]),
        ]

        constraints = [
            models.CheckConstraint(
                name="center_contact_person_has_name",
                condition=(
                    Q(
                        center_contact_type=(
                            Choices_Center_Contact_Type.INSTITUTION.value
                        )
                    )
                    | Q(first_name__gt="")
                    | Q(last_name__gt="")
                ),
            ),
            models.CheckConstraint(
                name="center_contact_institution_has_name",
                condition=(
                    Q(
                        center_contact_type=(
                            Choices_Center_Contact_Type.PERSON.value
                        )
                    )
                    | Q(institution_name__gt="")
                ),
            ),
            models.UniqueConstraint(
                fields=["veterinary_center", "document_id"],
                condition=(
                    ~Q(document_id="")
                    & Q(soft_deleted_at__isnull=True)
                ),
                name=UNIQUE_CENTER_CONTACT_DOCUMENT_ID_PER_CENTER,
            ),
        ]

    @property
    def name(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        if (
            self.center_contact_type
            == Choices_Center_Contact_Type.INSTITUTION.value
        ):
            return self.institution_name or "Institución sin nombre"

        full_name = f"{self.first_name} {self.last_name}".strip()

        return full_name or "Persona sin nombre"

    def clean(self) -> None:
        super().clean()

        self.center_contact_type = _clean_string(
            self.center_contact_type,
        )

        self.first_name = _clean_string(self.first_name)
        self.last_name = _clean_string(self.last_name)
        self.institution_name = _clean_string(self.institution_name)

        if self.document_id:
            self.document_id = _validate_and_normalize_chilean_document_id(
                self.document_id,
            )
        else:
            self.document_id = ""

        self.email = _clean_string(self.email).lower()
        self.primary_phone = _clean_string(self.primary_phone)
        self.secondary_phone = _clean_string(self.secondary_phone)
        self.tertiary_phone = _clean_string(self.tertiary_phone)
        self.address = _clean_string(self.address)
        self.city = _clean_string(self.city)
        self.region = _clean_string(self.region)
        self.country = _clean_string(self.country)
        self.notes = _clean_string(self.notes)

        if (
            self.center_contact_type
            == Choices_Center_Contact_Type.PERSON.value
        ):
            if not self.first_name and not self.last_name:
                raise ValidationError(
                    {
                        "first_name": (
                            "Debes indicar al menos nombre o apellido "
                            "para una persona."
                        ),
                        "last_name": (
                            "Debes indicar al menos nombre o apellido "
                            "para una persona."
                        ),
                    }
                )

            self.institution_name = ""

        elif (
            self.center_contact_type
            == Choices_Center_Contact_Type.INSTITUTION.value
        ):
            if not self.institution_name:
                raise ValidationError(
                    {
                        "institution_name": (
                            "El nombre de la institución es obligatorio."
                        ),
                    }
                )

            self.first_name = ""
            self.last_name = ""

        else:
            raise ValidationError(
                {
                    "center_contact_type": "Tipo de contacto inválido.",
                }
            )

        if self.soft_deleted_at is not None:
            self.is_active = False

    def __str__(self) -> str:
        return self.display_name


class Image(
    TrimFieldsMixin,
    SoftDeleteAuditValidationMixin,
    FullCleanOnSaveMixin,
    models.Model,
):
    """
    Propósito:
    Representa una imagen almacenada, por ejemplo en Cloudinary.

    Uso típico:
    - Logo del centro.
    - Imágenes administrativas.
    - Recursos visuales reutilizables.

    No dejo reverse relation desde Veterinary_Center porque normalmente
    estas imágenes se consultan directamente por filtros, no desde center.images.
    """

    image_name = models.CharField(
        max_length=NAMES_MAX_LENGTH,
        default="",
    )

    image_original_name = models.CharField(
        max_length=NAMES_MAX_LENGTH,
        default="",
    )

    image_public_id = models.CharField(
        max_length=CLOUDINARY_PUBLIC_ID_MAX_LENGTH,
        default="",
    )

    image_resource_type = models.CharField(
        max_length=CLOUDINARY_RESOURCE_TYPE_MAX_LENGTH,
        default="",
    )

    image_url = models.URLField(
        max_length=URLS_MAX_LENGTH,
        default="",
    )

    finished_setting_image = models.BooleanField(
        default=False,
    )

    image_creation_date = models.DateField(
        auto_now_add=True,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name="+",
    )

    soft_deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
    )

    soft_deleted_by = models.ForeignKey(
        Center_Staff_Membership_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    if TYPE_CHECKING:
        id: int
        veterinary_center_id: int
        soft_deleted_by_id: int | None

    class Meta:
        indexes = [
            models.Index(fields=["veterinary_center", "soft_deleted_at"]),
            models.Index(fields=["veterinary_center", "finished_setting_image"]),
            models.Index(fields=["image_public_id"]),
        ]

    def clean(self) -> None:
        super().clean()

        self.image_name = _clean_string(self.image_name)
        self.image_original_name = _clean_string(self.image_original_name)
        self.image_public_id = _clean_string(self.image_public_id)
        self.image_resource_type = _clean_string(self.image_resource_type)
        self.image_url = _clean_string(self.image_url)

    def __str__(self) -> str:
        if self.image_original_name:
            return self.image_original_name

        if self.image_name:
            return self.image_name

        return self.image_public_id


__all__ = [
    "Veterinary_Center",
    "Veterinary_Center_Settings",
    "Center_Clinical_Focus",
    "Center_Staff_Membership",
    "Personnel_Login_Session",
    "Center_Contact",
    "Image",
]