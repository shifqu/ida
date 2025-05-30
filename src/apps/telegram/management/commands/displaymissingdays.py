"""Django command to send a reminder to active users with a chat_id."""

from django.core.management.base import BaseCommand
from django.utils import translation

from apps.telegram.bot import Bot
from apps.telegram.models import TelegramSettings


class Command(BaseCommand):
    """Send a reminder via telegram."""

    help = "Send a text message to display the missing days in their timesheets."

    def handle(self, *_args, **_options):
        """Send a text message to display the missing days in their timesheets.

        References:
        https://core.telegram.org/bots/api#sendmessage

        Note:
        The chat_id is configured on the user as a TelegramSetting.
        """
        for setting in TelegramSettings.objects.filter(user__is_active=True):
            translation.activate(setting.user.language)
            Bot.display_missing_days(setting.chat_id, user=setting.user)
            translation.deactivate()
            self.stdout.write(self.style.SUCCESS(f"Successfully sent the message to {setting.user}."))
