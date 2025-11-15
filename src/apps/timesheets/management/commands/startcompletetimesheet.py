"""Django command to start the CompleteTimesheet command for active users with a chat_id."""

from django.utils import timezone
from django_telegram_app.management.base import BaseTelegramCommand

from apps.timesheets.telegrambot.commands.completetimesheet import Command as CompleteTimesheetCommand


class Command(BaseTelegramCommand):
    """Start the CompleteTimesheet command."""

    help = "Start the CompleteTimesheet command to let users complete their timesheets."
    command = CompleteTimesheetCommand

    def should_run(self):
        """Only run the command if it's the last day of the month."""
        today = timezone.now().date()
        tomorrow = today + timezone.timedelta(days=1)
        return tomorrow.day == 1
