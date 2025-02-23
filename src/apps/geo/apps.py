"""Geo app configuration."""

from django.apps import AppConfig


class GeoConfig(AppConfig):
    """Represent the geo AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.geo"
