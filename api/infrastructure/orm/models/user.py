# api/infrastructure/orm/models/user.py

from __future__ import annotations

from typing import Any, TYPE_CHECKING

import pyotp

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

from api.shared.orm.mixins import FullCleanOnSaveMixin, TrimFieldsMixin
from api.shared.utils.normalize_document_id import (
    is_valid_chilean_rut,
    normalize_document_id,
)


def _clean_string(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value).strip()

    return value.strip()


def _normalize_document_id_for_country(
    *,
    country_code: str,
    document_id: str,
) -> str:
    clean_country_code = _clean_string(country_code).upper()
    clean_document_id = _clean_string(document_id).upper()

    if not clean_document_id:
        return ""

    if clean_country_code == "CL":
        normalized_document_id = normalize_document_id(clean_document_id)

        if not is_valid_chilean_rut(normalized_document_id):
            raise ValidationError(
                {
                    "document_id": "El RUT chileno indicado no es válido.",
                }
            )

        return normalized_document_id

    return clean_document_id


class Pet_Control_User_Manager(BaseUserManager["Pet_Control_User"]):
    use_in_migrations = True

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "Pet_Control_User":
        clean_email = self.normalize_email(
            _clean_string(email),
        ).lower()

        if not clean_email:
            raise ValueError("El correo electrónico es obligatorio.")

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(
            email=clean_email,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "Pet_Control_User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self.create_user(
            email=email,
            password=password,
            **extra_fields,
        )


class Pet_Control_User(
    TrimFieldsMixin,
    FullCleanOnSaveMixin,
    AbstractBaseUser,
    PermissionsMixin,
):
    """
    Propósito:
    Representa la cuenta global de una persona en Pet Control.

    Importante:
    - Este modelo maneja el login global.
    - No pertenece a ningún centro veterinario.
    - Una misma persona puede trabajar en varios centros veterinarios.
    - El rol local vive en Center_Staff_Membership.
    """

    email = models.EmailField(
        unique=True,
        db_index=True,
    )

    first_name = models.CharField(
        max_length=255,
    )

    last_name = models.CharField(
        max_length=255,
    )

    document_id = models.CharField(
        max_length=20,
    )

    country_code = models.CharField(
        max_length=10,
    )

    cell_phone = models.CharField(
        max_length=20,
    )

    complete_address = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )

    totp_secret = models.CharField(
        max_length=32,
        blank=True,
        null=True,
    )

    is_2fa_enabled = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    is_staff = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    if TYPE_CHECKING:
        id: int

    objects = Pet_Control_User_Manager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
        "country_code",
        "document_id",
        "cell_phone",
    ]

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["country_code", "document_id"]),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["country_code", "document_id"],
                name="unique_pet_control_user_country_document_id",
            ),
        ]

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def generate_totp(self) -> pyotp.TOTP:
        if not self.totp_secret:
            self.totp_secret = pyotp.random_base32()
            self.save(update_fields=["totp_secret"])

        return pyotp.TOTP(self.totp_secret)

    def clean(self) -> None:
        super().clean()

        self.email = _clean_string(self.email).lower()
        self.first_name = _clean_string(self.first_name)
        self.last_name = _clean_string(self.last_name)
        self.country_code = _clean_string(self.country_code).upper()
        self.cell_phone = _clean_string(self.cell_phone)

        if self.complete_address:
            self.complete_address = _clean_string(self.complete_address)
        else:
            self.complete_address = None

        if self.document_id:
            self.document_id = _normalize_document_id_for_country(
                country_code=self.country_code,
                document_id=self.document_id,
            )
        else:
            self.document_id = ""

        if self.totp_secret:
            self.totp_secret = _clean_string(self.totp_secret)
        else:
            self.totp_secret = None

        if not self.email:
            raise ValidationError(
                {
                    "email": "El correo electrónico es obligatorio.",
                }
            )

        if not self.first_name:
            raise ValidationError(
                {
                    "first_name": "El nombre es obligatorio.",
                }
            )

        if not self.last_name:
            raise ValidationError(
                {
                    "last_name": "El apellido es obligatorio.",
                }
            )

        if not self.country_code:
            raise ValidationError(
                {
                    "country_code": "El país del documento es obligatorio.",
                }
            )

        if not self.document_id:
            raise ValidationError(
                {
                    "document_id": "El documento de identidad es obligatorio.",
                }
            )

        if not self.cell_phone:
            raise ValidationError(
                {
                    "cell_phone": "El teléfono celular es obligatorio.",
                }
            )

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"
    
    
__all__ = [
    "Pet_Control_User",
    "Pet_Control_User_Manager",
]