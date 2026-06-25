# api/infrastructure/orm/models/audit.py

from __future__ import annotations

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from api.infrastructure.orm.models.center import Veterinary_Center


class Audit_Log(models.Model):
    """
    Generic audit trail entry.

    Stores who changed what, in which center, when it happened,
    and the before/after values.
    """

    class Action(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"
        SOFT_DELETE = "SOFT_DELETE", "Soft delete"
        RESTORE = "RESTORE", "Restore"

    veterinary_center = models.ForeignKey(
        Veterinary_Center,
        on_delete=models.PROTECT,
        related_name="+",
    )

    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    actor_display_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    actor_role = models.CharField(
        max_length=80,
        blank=True,
        default="",
    )

    action = models.CharField(
        max_length=40,
        choices=Action.choices,
    )

    entity_type = models.CharField(
        max_length=120,
    )

    entity_id = models.PositiveBigIntegerField()

    old_values = models.JSONField(
        encoder=DjangoJSONEncoder,
        default=dict,
        blank=True,
    )

    new_values = models.JSONField(
        encoder=DjangoJSONEncoder,
        default=dict,
        blank=True,
    )

    reason = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        encoder=DjangoJSONEncoder,
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "api_audit_log"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["veterinary_center", "entity_type", "entity_id"],
                name="audit_log_entity_idx",
            ),
            models.Index(
                fields=["veterinary_center", "created_at"],
                name="audit_log_center_date_idx",
            ),
            models.Index(
                fields=["actor_user", "created_at"],
                name="audit_log_actor_date_idx",
            ),
            models.Index(
                fields=["action"],
                name="audit_log_action_idx",
            ),
        ]

    def __str__(self) -> str:
        actor_identifier = self.actor_display_name or str(
            getattr(self, "actor_user_id", "") or "system"
        )

        return (
            f"{self.action} {self.entity_type}:{self.entity_id} "
            f"by {actor_identifier}"
        )