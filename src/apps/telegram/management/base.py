"""Base command for telegram management commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.translation import override
from django_telegram_app.bot.bot import handle_update
from django_telegram_app.management.base import BaseTelegramCommand

from apps.telegram.models import TelegramSettings
from apps.users.models import IdaUser

if TYPE_CHECKING:
    from django_telegram_app.models import AbstractTelegramSettings


class IdaBaseTelegramCommand(BaseTelegramCommand):
    """Base command for telegram management commands."""

    def get_telegram_settings_filter(self):
        """Filter to get only active users."""
        return {"user__is_active": True}

    def handle_command(self, telegram_settings: AbstractTelegramSettings, command_text: str):
        """Handle the update in the current user's language."""
        assert isinstance(telegram_settings, TelegramSettings)
        assert isinstance(telegram_settings.user, IdaUser)

        update = {"message": {"chat": {"id": telegram_settings.chat_id}, "text": command_text}}
        with override(telegram_settings.user.language):
            handle_update(update, telegram_settings)
