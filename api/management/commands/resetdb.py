# api/management/commands/resetdb.py

from typing import Any

from django.core.management.base import BaseCommand
from django.conf import settings

import psycopg
from psycopg import sql
from psycopg.connection import Connection
from psycopg.cursor import Cursor


class Command(BaseCommand):
    help: str = "Drops and recreates the database. Run migrations manually afterward."

    def handle(
        self,
        *args: Any,
        **options: Any,
    ) -> None:

        db_settings: dict[str, Any] = settings.DATABASES["default"]

        db_name: str = str(db_settings["NAME"])
        db_user: str = str(db_settings["USER"])
        db_password: str = str(db_settings.get("PASSWORD", ""))
        db_host: str = str(db_settings.get("HOST", "localhost"))
        db_port: str = str(db_settings.get("PORT", "5432"))

        self.stdout.write(
            f"Dropping and recreating database '{db_name}'..."
        )

        conn: Connection[Any]

        with psycopg.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            autocommit=True,
        ) as conn:

            cur: Cursor[Any]

            with conn.cursor() as cur:

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
                "Now run: python manage.py migrate"
            )
        )
