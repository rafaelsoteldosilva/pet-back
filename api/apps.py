# api/apps.py

from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self) -> None:
        import api.infrastructure.events.handlers  # pyright: ignore[reportUnusedImport]
