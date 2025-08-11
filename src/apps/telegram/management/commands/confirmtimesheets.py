"""Django command to send a request to confirm their timesheet to active users with a chat_id."""

from django.core.management.base import BaseCommand
from django.utils import timezone, translation

from apps.telegram.bot.core import Bot
from apps.telegram.models import TelegramSettings


class Command(BaseCommand):
    """Send a reminder via telegram."""

    help = "Send a text message to request a user to confirm their timesheets."

    def add_arguments(self, parser):
        """Add command line arguments."""
        now = timezone.now()
        parser.add_argument("--month", type=int, default=now.month, help=f"Month (1-12), default {now.month}")
        parser.add_argument("--year", type=int, default=now.year, help=f"Year (e.g. 2025), default {now.year}")
        parser.add_argument(
            "--project_id", type=int, default=0, help="ID of the project, if not provided, all projects will be used."
        )

    def handle(self, *_args, **options):
        """Send a text message to request a user to confirm their timesheets.

        References:
        https://core.telegram.org/bots/api#sendmessage

        Note:
        The chat_id is configured on the user as a TelegramSetting.
        """
        month = options["month"]
        year = options["year"]
        project_id = options["project_id"]
        for setting in TelegramSettings.objects.filter(user__is_active=True):
            translation.activate(setting.user.language)
            sent_message = Bot.request_user_to_confirm_timesheets(setting.chat_id, user=setting.user)
            translation.deactivate()
            if sent_message:
                self.stdout.write(self.style.SUCCESS(f"Successfully sent the message to {setting.user}."))
            else:
                self.stdout.write(self.style.WARNING(f"No missing days for {setting.user}."))
