"""Shared CLI option types for django-octave."""

from __future__ import annotations

from enum import StrEnum


class DatabaseChoice(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
    MARIADB = "mariadb"
