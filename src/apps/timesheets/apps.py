"""Timesheets app configuration."""

from django.apps import AppConfig


class TimesheetsConfig(AppConfig):
    """Represent the timesheets AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.timesheets"
