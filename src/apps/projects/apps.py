"""Projects app configuration."""

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    """Represent the projects AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
