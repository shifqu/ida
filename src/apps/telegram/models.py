"""Models for the telegram app."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_telegram_app.models import AbstractTelegramSettings


class TelegramSettings(AbstractTelegramSettings):
    """Custom Telegram settings model."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("user"))
