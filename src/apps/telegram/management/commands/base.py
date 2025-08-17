"""Base command module to start telegram commands.

Note:
This module's command-class does not create an actual CLI command, but can be used by actual commands.
"""

from django.core.management.base import BaseCommand
from django.utils import translation

from apps.telegram.bot.core import Bot
from apps.telegram.models import TelegramSettings


class TelegramCommand(BaseCommand):
    """Base command class to start Telegram bot commands."""

    command_text: str = ""

    def handle(self, *_args, **_options):
        """Start the configured telegram command.

        Note:
        The chat_id is configured on the user as a TelegramSetting.
        A fake update is created with a message containing the command, this is not persisted.
        """
        if not self.command_text:
            raise ValueError("The attribute command_text must be set.")

        for settings in TelegramSettings.objects.filter(user__is_active=True):
            translation.activate(settings.user.language)
            update = {"message": {"chat": {"id": settings.chat_id}, "text": self.command_text}}
            Bot.handle(update=update)
            translation.deactivate()
            self.stdout.write(self.style.SUCCESS(f"Started the command for {settings.user}."))
