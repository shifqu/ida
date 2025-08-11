"""Django command to start a RegisterWork flow for active users with a chat_id."""

from django.core.management.base import BaseCommand
from django.utils import translation

from apps.telegram.bot.commands.registerwork import RegisterWork
from apps.telegram.models import TelegramSettings
from apps.telegram.types import TelegramUpdate


class Command(BaseCommand):
    """Start a RegisterWork flow."""

    help = "Start a RegisterWork flow to let users register their work hours."

    def handle(self, *_args, **_options):
        """Start a RegisterWork flow to let users register their work hours.

        References:
        https://core.telegram.org/bots/api#sendmessage

        Note:
        The chat_id is configured on the user as a TelegramSetting.
        A fake TelegramUpdate is created with a message containing the command "/registerwork", this is not persisted.
        """
        for settings in TelegramSettings.objects.filter(user__is_active=True):
            translation.activate(settings.user.language)
            telegram_update = TelegramUpdate({"message": {"chat": {"id": settings.chat_id}, "text": "/registerwork"}})
            RegisterWork(settings=settings).start(telegram_update)
            translation.deactivate()
            self.stdout.write(self.style.SUCCESS(f"Started the flow for {settings.user}."))
