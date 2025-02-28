"""Invoices app configuration."""

from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    """Represent the invoices AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.invoices"
