# api/models.py

"""
Django model registration bridge.

The real ORM models live in:
    api/infrastructure/orm/models/

Django discovers models through this module because the installed app is:
    api.apps.ApiConfig

So this file imports the infrastructure models and registers them under
the `api` app label.

This is especially important for:
    AUTH_USER_MODEL = "api.Pet_Control_User"
"""

from api.infrastructure.orm.models import *