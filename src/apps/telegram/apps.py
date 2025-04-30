"""Telegram app configuration."""

from django.apps import AppConfig


class TelegramConfig(AppConfig):
    """Represent the telegram AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram"
