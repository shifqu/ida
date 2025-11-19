"""Configuration for the telegram app."""

from django.apps import AppConfig


class TelegramConfig(AppConfig):
    """Configuration for the telegram app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram"
