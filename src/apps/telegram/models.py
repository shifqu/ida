"""Telegram models."""

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _


class Message(models.Model):
    """Represent a Telegram Message.

    The raw message from the Telegram API is stored as json.
    Some fields often used by the bot are stored as separate fields.

    Reference:
    https://core.telegram.org/bots/api#message
    """

    raw_message = models.JSONField()
    error = models.TextField(null=True, blank=True)

    def __str__(self):
        """Return the string representation of the message."""
        return str(self.raw_message.get("update_id", "unknown"))

    class Meta:
        """Set meta options."""

        verbose_name = _("message")
        verbose_name_plural = _("messages")


class TelegramSettings(models.Model):
    """Represent telegram settings."""

    if TYPE_CHECKING:
        from apps.users.models import IdaUser

        user: models.OneToOneField[IdaUser]

    user = models.OneToOneField("users.IdaUser", on_delete=models.CASCADE)
    chat_id = models.CharField(verbose_name=_("chat id"), unique=True, max_length=255)

    class Meta:
        """Set meta options."""

        verbose_name = _("telegram setting")
        verbose_name_plural = _("telegram settings")

    def __str__(self):
        """Return a string representation of the telegram setting."""
        return f"{self.user.username} ({self.chat_id})"
