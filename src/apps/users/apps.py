"""Users app config."""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Represent the Users AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
