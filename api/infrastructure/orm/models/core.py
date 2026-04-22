# api/infrastructure/orm/models/core.py

from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


from typing import Any, TYPE_CHECKING


from api.shared.choices.choices import (
    Choices_DiagnosticCodingSystem,
    Choices_ContactType,
    Choices_Role,
)

from api.shared.constants.constants import *
from api.shared.utils.normalize_dni import normalize_dni

import pyotp

from api.shared.http.mixins import TrimFieldsMixin

# Models located in api/infrastructure/orm/models/core.py:
# Models: Veterinary_Center, Vet_Clinical_Focus, Vet_Center_Personnel, Personnel_Login_Session, Contact,
# Models: Image,


class Veterinary_Center(TrimFieldsMixin, models.Model):
    """
    Propósito: Entidad raíz del dominio. Todo vive dentro de un centro veterinario. Aísla datos, reglas, 
    catálogos y operaciones por clínica.
    """
    name = models.CharField(max_length=120)
    country_code = models.CharField(max_length=5)
    email = models.EmailField()
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    clinic_code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code used for history codes",
    )
    diagnostic_code_system = models.CharField(
        max_length=20,
        choices=Choices_DiagnosticCodingSystem.choices,
        default=Choices_DiagnosticCodingSystem.INTERNAL,
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Centro activo"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        follow_up_categories: Any
        center_settings: "Veterinary_Center_Settings"

    def __str__(self):
        return self.name
    
class Veterinary_Center_Settings(models.Model):
    """
    Propósito:
    Configuración global del centro veterinario.

    Para qué sirve:
    - Definir identidad del centro
    - Configurar comportamiento del sistema
    - Controlar especies permitidas
    - Branding y UI
    """

    veterinary_center = models.OneToOneField(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_SETTINGS_RN,
    )

    # ========================
    # 🏥 IDENTIDAD
    # ========================
    name = models.CharField(
        max_length=150,
        verbose_name="Nombre comercial"
    )

    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?[\d\s\-]+$",
                message="Número de teléfono inválido."
            )
        ],
        verbose_name="Teléfono"
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Correo electrónico"
    )

    address = models.CharField(
        max_length=255,
        verbose_name="Dirección"
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    country = models.CharField(
        max_length=100,
        default="Chile"
    )

    # ========================
    # 🐾 ESPECIES PERMITIDAS
    # ========================
    allowed_species = models.ManyToManyField(
        SPECIES_IN_CENTER_MODEL,
        blank=True,
        related_name=ALLOWED_SPECIES_CENTER_SETTINGS_RN,
        verbose_name="Especies permitidas"
    )

    # ========================
    # ⚙️ CONFIGURACIÓN OPERATIVA
    # ========================
    default_consultation_duration = models.PositiveIntegerField(
        default=30,
        verbose_name="Duración consulta (minutos)"
    )

    allow_emergency_attention = models.BooleanField(
        default=True,
        verbose_name="Atiende urgencias"
    )

    require_microchip_for_surgery = models.BooleanField(default=True)
    require_microchip_for_hospitalization = models.BooleanField(default=False)
    require_microchip_for_consultation = models.BooleanField(default=False)

    # ========================
    # 🧾 NUMERACIÓN / CÓDIGOS
    # ========================
    pet_history_code_prefix = models.CharField(
        max_length=10,
        default="PET",
        verbose_name="Prefijo ficha paciente"
    )

    auto_generate_history_code = models.BooleanField(
        default=True
    )

    # ========================
    # 🎨 BRANDING / UI
    # ========================
    logo_url = models.URLField(
        blank=True,
        null=True,
        verbose_name="Logo del centro"
    )

    primary_color = models.CharField(
        max_length=7,
        default="#3b82f6",
        verbose_name="Color principal"
    )

    secondary_color = models.CharField(
        max_length=7,
        default="#10b981",
        verbose_name="Color secundario"
    )

    # ========================
    # 🔔 NOTIFICACIONES
    # ========================
    send_vaccine_reminders = models.BooleanField(
        default=True
    )

    send_followup_reminders = models.BooleanField(
        default=True
    )

    # ========================
    # 📊 CONTROL / AUDITORÍA
    # ========================
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Settings - {self.name}"
    
class Vet_Clinical_Focus(models.Model):
    """
    Propósito: Define un enfoque clínico profesional que puede tener un veterinario.
    Ej: Dermatología, Cirugía, Medicina Felina, Cardiología, etc.
    """

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable machine-readable code (dermatology, surgery, etc.)"
    )

    label = models.CharField(
        max_length=100,
        help_text="Human readable label"
    )

    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional detailed explanation of this focus"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["label"]

    def __str__(self):
        return self.label
    
class Vet_Center_Personnel(TrimFieldsMixin, models.Model):
    """
    Propósito: Usuarios internos del centro: veterinarios, asistentes, administrativos.
    """
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    national_dni = models.CharField(max_length=20)
    country_code = models.CharField(max_length=10)
    cell_phone = models.CharField(max_length=20)
    complete_address = models.CharField(max_length=200, blank=True, null=True)

    password_hash = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=Choices_Role.choices)

    totp_secret = models.CharField(max_length=32, blank=True, null=True)
    is_2fa_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    clinical_focuses = models.ManyToManyField(
        VET_CLINICAL_FOCUS_MODEL,
        related_name=CLINICAL_FOCUSES_VETERINARIANS_RN,
        blank=True,
    )

    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE
    )
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["country_code", "national_dni", "veterinary_center"],
                name=UNIQUE_VET_CENTER_PERSONNEL_CENTER_COUNTRY_DNI
            )
        ]

    if TYPE_CHECKING:
        personnel_login_sessions: Any
        
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def is_currently_logged_in(self):
        return self.personnel_login_sessions.filter(logout_at__isnull=True).exists()

    def generate_totp(self):
        if not self.totp_secret:
            self.totp_secret = pyotp.random_base32()
            self.save(update_fields=["totp_secret"])
        return pyotp.TOTP(self.totp_secret)

    def clean(self):
        super().clean()
        if self.country_code:
            self.country_code = self.country_code.upper()
        if self.national_dni:
            self.national_dni = normalize_dni(self.national_dni)

    def save(self, *args: Any, **kwargs: Any):
        if self.national_dni:
            self.national_dni = normalize_dni(self.national_dni)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.role})"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return True
    
class Personnel_Login_Session(models.Model):
    """
    Propósito: Auditoría de sesiones de login.
    """
    personnel = models.ForeignKey(
        VET_CENTER_PERSONNEL_MODEL,
        on_delete=models.CASCADE,
        related_name=PERSONNEL_LOGIN_SESSIONS_RN
    )
    
    login_at = models.DateTimeField()
    logout_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-login_at"]

    def __str__(self):
        out = self.logout_at.strftime("%Y-%m-%d %H:%M") if self.logout_at else "ACTIVE"
        return f"{self.personnel.first_name} — {self.login_at} → {out}"

class Contact(TrimFieldsMixin, models.Model):
    """
    Propósito: Personas o instituciones externas: dueños, responsables, clínicas, fundaciones.
    """
    contact_type = models.CharField(
        max_length=20,
        choices=Choices_ContactType.choices,
        default=Choices_ContactType.PERSON,
        help_text="Define si el contacto es una persona natural o una institución"
    )
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    institution = models.CharField(max_length=100, blank=True, null=True)
    country_code = models.CharField(max_length=2)
    national_dni = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    cell_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(INTERNATIONAL_PHONE_NUMBER_REGEX)],
    )
    home_phone = models.CharField(max_length=20, blank=True, null=True)
    work_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    observations = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["country_code", "national_dni", "veterinary_center"],
                name=UNIQUE_CONTACT_CENTER_COUNTRY_DNI
            )
        ]
        ordering = ["last_name", "first_name"]
        
    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"
        
    def clean(self):
        super().clean()
        if self.country_code:
            self.country_code = self.country_code.upper()
        if self.national_dni:
            self.national_dni = self.national_dni.upper()

        if self.contact_type == Choices_ContactType.PERSON:
            if not (self.first_name and self.last_name):
                raise ValidationError({
                    "first_name": "Nombre y apellido son obligatorios para personas."
                })

        if self.contact_type == Choices_ContactType.INSTITUTION:
            if not self.institution:
                raise ValidationError({
                    "institution": "La institución es obligatoria para este tipo de contacto."
                })

    def save(self, *args: Any, **kwargs: Any):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        if self.contact_type == Choices_ContactType.INSTITUTION:
            return self.institution or Choices_ContactType.INSTITUTION
        return f"{self.first_name or ''} {self.last_name or ''}".strip()


class Image(models.Model):
    """
    Propósito: representa una imagen almacenada (Cloudinary u otro backend).
    """
    image_name = models.CharField(max_length=NAMES_MAX_LENGTH, default="")
    image_original_name = models.CharField(max_length=NAMES_MAX_LENGTH, default="")
    image_public_id = models.CharField(max_length=CLOUDINARY_PUBLIC_ID_MAX_LENGTH, default="")
    image_resource_type = models.CharField(max_length=CLOUDINARY_RESOURCE_TYPE_MAX_LENGTH, default="")
    image_url = models.URLField(max_length=URLS_MAX_LENGTH, default="")
    finished_setting_image = models.BooleanField(default=False)
    image_creation_date = models.DateField(auto_now_add=True)
    veterinary_center = models.ForeignKey(
        VETERINARY_CENTER_MODEL,
        on_delete=models.CASCADE,
        related_name=CENTER_IMAGES_RN
    )
    
    def __str__(self) -> str:
        if self.image_original_name:
            return self.image_original_name
        if self.image_name:
            return self.image_name
        return self.image_public_id
    
__all__ = [
    "Veterinary_Center", 
    "Vet_Clinical_Focus", 
    "Vet_Center_Personnel", 
    "Personnel_Login_Session", 
    "Contact",
    "Image", 
]
