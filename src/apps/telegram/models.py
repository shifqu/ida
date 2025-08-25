"""Telegram models."""

import calendar
import uuid
from typing import TYPE_CHECKING, Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.timesheets.models import TimesheetItem


class Message(models.Model):
    """Represent a Telegram Message.

    The raw message from the Telegram API is stored as json.

    Reference:
    https://core.telegram.org/bots/api#message
    """

    raw_message = models.JSONField(verbose_name=_("raw message"))
    error = models.TextField(verbose_name=_("error"), null=True, blank=True)

    @property
    def message_truncated(self):
        """Return the message truncated to 100 characters."""
        message_str = str(self.raw_message)
        if len(message_str) > 100:
            return message_str[:97] + "..."
        return message_str

    @property
    def update_id(self) -> int:
        """Return the chat id from the raw message."""
        return self.raw_message.get("update_id", "unknown")

    def __str__(self):
        """Return the string representation of the message."""
        if self.error:
            return f"{self.update_id} - {self.error}"
        return str(self.update_id)

    class Meta:
        """Set meta options."""

        verbose_name = _("message")
        verbose_name_plural = _("messages")


class TelegramSettings(models.Model):
    """Represent telegram settings."""

    if TYPE_CHECKING:
        from apps.users.models import IdaUser

        user: models.OneToOneField[IdaUser]
        data: models.JSONField[dict[str, str]]

    user = models.OneToOneField("users.IdaUser", on_delete=models.CASCADE, verbose_name=_("user"))
    chat_id = models.IntegerField(verbose_name=_("chat id"), unique=True)
    data = models.JSONField(verbose_name=_("data"), default=dict, blank=True, encoder=DjangoJSONEncoder)
    updated_at = models.DateTimeField(verbose_name=_("updated at"), auto_now=True)

    class Meta:
        """Set meta options."""

        verbose_name = _("telegram setting")
        verbose_name_plural = _("telegram settings")

    def __str__(self):
        """Return a string representation of the telegram setting."""
        return f"{self.user.username} ({self.chat_id})"


class CallbackData(models.Model):
    """Store callback data for Telegram inline keyboards.

    This is required because telegram limits the size of callback data to 64 bytes.
    """

    if TYPE_CHECKING:
        data: models.JSONField[dict[str, Any]]

    token = models.UUIDField(verbose_name=_("token"), default=uuid.uuid4, unique=True, db_index=True)
    command = models.CharField(verbose_name=_("command"), max_length=255)
    step = models.CharField(verbose_name=_("step"), max_length=255)
    data = models.JSONField(verbose_name=_("callback data"), default=dict, encoder=DjangoJSONEncoder)
    created_at = models.DateTimeField(verbose_name=_("created at"), auto_now_add=True)

    class Meta:
        """Set meta options."""

        verbose_name = _("callback data")
        verbose_name_plural = _("callback data")
        indexes = [models.Index(models.F("data__correlation_key"), name="callback_correlation_key_idx")]

    def __str__(self):
        """Return a string representation of the callback data."""
        return f"{self.token} - {self.data}"

    @property
    def data_truncated(self):
        """Return the data truncated to 100 characters."""
        data_str = str(self.data)
        if len(data_str) > 100:
            return data_str[:97] + "..."
        return data_str


class BaseItemTypeRule(models.Model):
    """Represent an abstract base rule to infer the item type of a timesheet item."""

    item_type = models.CharField(max_length=50, choices=TimesheetItem.ItemType.choices, verbose_name=_("item type"))

    class Meta:
        """Make the model abstract."""

        abstract = True

    if TYPE_CHECKING:

        def get_item_type_display(self) -> str: ...  # noqa: D102


class WeekdayItemTypeRule(BaseItemTypeRule):
    """Represent a weekday rule to infer the item type of a timesheet item."""

    weekday = models.IntegerField(choices=[(i, calendar.day_name[i]) for i in range(7)])

    def __str__(self):
        """Return the string representation of the weekday item type rule."""
        return f"Weekday rule: {self.weekday} - {self.get_item_type_display()}"


class TimeRangeItemTypeRule(BaseItemTypeRule):
    """Represent a time range rule to infer the item type of a timesheet item."""

    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        """Return the string representation of the time range item type rule."""
        return f"Time range rule: {self.start_time} - {self.end_time} ({self.get_item_type_display()})"
