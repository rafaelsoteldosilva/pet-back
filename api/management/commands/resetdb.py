# api/management/commands/resetdb.py

from __future__ import annotations

from typing import Any

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from psycopg import sql


PROTECTED_DATABASE_NAMES = {
    "postgres",
    "template0",
    "template1",
}


class Command(BaseCommand):
    help = "Drops and recreates the PostgreSQL database. Run migrations manually afterward."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Allow reset even when DEBUG is False.",
        )

    def handle(
        self,
        *args: Any,
        **options: Any,
    ) -> None:
        force = bool(options.get("force", False))

        if not settings.DEBUG and not force:
            raise CommandError(
                "Refusing to reset the database because DEBUG is False. "
                "Use --force only if you are completely sure."
            )

        db_settings: dict[str, Any] = settings.DATABASES["default"]

        engine = str(db_settings.get("ENGINE", ""))

        if "postgresql" not in engine:
            raise CommandError(
                "resetdb only supports PostgreSQL databases."
            )

        db_name = str(db_settings["NAME"])
        db_user = str(db_settings["USER"])
        db_password = str(db_settings.get("PASSWORD", ""))
        db_host = str(db_settings.get("HOST", "localhost") or "localhost")
        db_port = str(db_settings.get("PORT", "5432") or "5432")

        if db_name in PROTECTED_DATABASE_NAMES:
            raise CommandError(
                f"Refusing to drop protected database '{db_name}'."
            )

        self.stdout.write(
            self.style.WARNING(
                f"Dropping and recreating database '{db_name}'..."
            )
        )

        with psycopg.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            autocommit=True,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid()
                    """,
                    (db_name,),
                )

                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        sql.Identifier(db_name)
                    )
                )

                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(db_name)
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "✅ Database recreated successfully."
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "1- Now delete both '0001_initial.py and 0002_preload_basic_data.py'"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "2- then run 'python manage.py makemigrations'"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "3- then create '0002_preload_basic_data.py'"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "4- and then run 'python manage.py migrate'"
            )
        )