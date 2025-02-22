"""Companies app configuration."""

from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    """Represent the companies AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.companies"
