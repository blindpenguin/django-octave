"""Pinned dependency constraints for generated projects.

Bump these in one place when cutting a django-octave release.
"""

from __future__ import annotations

# Generator targets the newest Python Django supports at release time.
GENERATED_PYTHON_VERSION = "3.13"

# Constraint strings embedded in generated pyproject.toml.
DJANGO = "Django>=5.2,<7"
DRF = "djangorestframework>=3.15,<4"
DRF_SPECTACULAR = "drf-spectacular[sidecar]>=0.28,<1"
SIMPLEJWT = "djangorestframework-simplejwt>=5.4,<6"
DJANGO_FILTER = "django-filter>=24.3,<26"
CORS_HEADERS = "django-cors-headers>=4.4,<5"
DJANGO_ENVIRON = "django-environ>=0.11,<1"
WHITENOISE = "whitenoise>=6.7,<7"
GUNICORN = "gunicorn>=23,<24"
PSYCOPG = "psycopg[binary]>=3.2,<4"
MYSQLCLIENT = "mysqlclient>=2.2,<3"
PYTEST = "pytest>=8,<10"
PYTEST_DJANGO = "pytest-django>=4.9,<5"
FACTORY_BOY = "factory-boy>=3.3,<4"
PYTEST_COV = "pytest-cov>=6,<8"
RUFF = "ruff>=0.9,<1"
CELERY = "celery[redis]>=5.4,<6"

ALWAYS_ON_DEPENDENCIES: tuple[str, ...] = (
    DJANGO,
    DRF,
    DRF_SPECTACULAR,
    SIMPLEJWT,
    DJANGO_FILTER,
    CORS_HEADERS,
    DJANGO_ENVIRON,
    WHITENOISE,
    GUNICORN,
)

DEV_DEPENDENCIES: tuple[str, ...] = (
    PYTEST,
    PYTEST_DJANGO,
    FACTORY_BOY,
    PYTEST_COV,
    RUFF,
)
