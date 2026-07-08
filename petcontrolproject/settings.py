# PET-BACK/petcontrolproject/settings.py

"""
Django settings for petcontrolproject project.
"""

from pathlib import Path
from corsheaders.defaults import default_headers
import os
from datetime import timedelta
from dotenv import load_dotenv
import django_stubs_ext

django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ======================================================
# ENV HELPERS
# ======================================================

def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    return raw_value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default or []

    return [
        item.strip()
        for item in raw_value.split(",")
        if item.strip()
    ]


# ======================================================
# BASIC SETTINGS
# ======================================================

DEBUG = env_bool("DJANGO_DEBUG", default=True)

IS_PRODUCTION = env_bool(
    "DJANGO_PRODUCTION",
    default=not DEBUG,
)

_secret_key_from_env = os.getenv("DJANGO_SECRET_KEY")

if _secret_key_from_env:
    _resolved_secret_key = _secret_key_from_env
elif DEBUG:
    _resolved_secret_key = (
        "django-insecure-dev-only-pet-control-change-this-in-production"
    )
else:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is required when DJANGO_DEBUG=False."
    )

SECRET_KEY = _resolved_secret_key

PUBLIC_API_KEY = os.getenv("PUBLIC_API_KEY")

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
    ],
)

AUTH_USER_MODEL = "api.Pet_Control_User"


# ======================================================
# CORS
# ======================================================

CORS_ALLOWED_ORIGINS = env_list(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
)

CORS_ALLOW_CREDENTIALS = env_bool(
    "DJANGO_CORS_ALLOW_CREDENTIALS",
    default=True,
)

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-api-key",
]


# ======================================================
# DJANGO REST FRAMEWORK
# ======================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),

    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("DRF_THROTTLE_ANON", "10/min"),
        "user": os.getenv("DRF_THROTTLE_USER", "1000/day"),
    },

    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "COERCE_DECIMAL_TO_STRING": False,

    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}


# ======================================================
# SIMPLE JWT
# ======================================================

JWT_ACCESS_TOKEN_MINUTES = env_int(
    "JWT_ACCESS_TOKEN_MINUTES",
    30 if IS_PRODUCTION else 240,
)

JWT_REFRESH_TOKEN_DAYS = env_int(
    "JWT_REFRESH_TOKEN_DAYS",
    7,
)

JWT_ROTATE_REFRESH_TOKENS = env_bool(
    "JWT_ROTATE_REFRESH_TOKENS",
    default=IS_PRODUCTION,
)

JWT_BLACKLIST_AFTER_ROTATION = env_bool(
    "JWT_BLACKLIST_AFTER_ROTATION",
    default=JWT_ROTATE_REFRESH_TOKENS,
)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=JWT_ACCESS_TOKEN_MINUTES,
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=JWT_REFRESH_TOKEN_DAYS,
    ),

    "ROTATE_REFRESH_TOKENS": JWT_ROTATE_REFRESH_TOKENS,
    "BLACKLIST_AFTER_ROTATION": JWT_BLACKLIST_AFTER_ROTATION,

    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",

    "AUTH_TOKEN_CLASSES": (
        "rest_framework_simplejwt.tokens.AccessToken",
    ),

    "TOKEN_TYPE_CLAIM": "token_type",
    "JTI_CLAIM": "jti",

    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",

    "UPDATE_LAST_LOGIN": False,
}


# ======================================================
# APPLICATIONS
# ======================================================

INSTALLED_APPS = [
    # Django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "django_extensions",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",

    # Local apps
    "api.apps.ApiConfig",
]


# ======================================================
# MIDDLEWARE
# ======================================================

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ======================================================
# URLS / TEMPLATES / WSGI
# ======================================================

ROOT_URLCONF = "petcontrolproject.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "petcontrolproject.wsgi.application"


# ======================================================
# DATABASE
# ======================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("LOCAL_DB_NAME"),
        "USER": os.getenv("LOCAL_DB_USER"),
        "PASSWORD": os.getenv("LOCAL_DB_PASSWORD"),
        "HOST": os.getenv("LOCAL_DB_HOST", "localhost"),
        "PORT": os.getenv("LOCAL_DB_PORT", "5432"),
    }
}


# ======================================================
# AUTHENTICATION
# ======================================================

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ======================================================
# INTERNATIONALIZATION
# ======================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")

USE_I18N = True

USE_TZ = True


# ======================================================
# STATIC FILES
# ======================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATIC_DIR = BASE_DIR / "static"

STATICFILES_DIRS = (
    [STATIC_DIR]
    if STATIC_DIR.exists()
    else []
)


# ======================================================
# SECURITY SETTINGS
# ======================================================

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[],
)

SECURE_SSL_REDIRECT = env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=IS_PRODUCTION,
)

SESSION_COOKIE_SECURE = env_bool(
    "DJANGO_SESSION_COOKIE_SECURE",
    default=IS_PRODUCTION,
)

CSRF_COOKIE_SECURE = env_bool(
    "DJANGO_CSRF_COOKIE_SECURE",
    default=IS_PRODUCTION,
)

SECURE_HSTS_SECONDS = env_int(
    "DJANGO_SECURE_HSTS_SECONDS",
    0,
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)

SECURE_HSTS_PRELOAD = env_bool(
    "DJANGO_SECURE_HSTS_PRELOAD",
    default=False,
)


# ======================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ======================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ======================================================
# LOGGING
# ======================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "django.log"),
            "formatter": "verbose",
        },
    },

    "loggers": {
        "django.server": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },

        "django": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": True,
        },

        "django.request": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },

        "django.security": {
            "handlers": ["file"],
            "level": "ERROR",
            "propagate": False,
        },

        "backend_access": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}