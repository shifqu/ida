"""Django command to start a RegisterWork command for active users with a chat_id."""

from django.utils import timezone

from apps.telegram.management.base import ManagementCommand
from apps.timesheets.telegrambot.commands.registerwork import Command as RegisterWorkCommand


class Command(ManagementCommand):
    """Start a RegisterWork command."""

    help = "Start a RegisterWork command to let users register their work hours."
    command = RegisterWorkCommand

    def should_run(self):
        """Only run on weekdays."""
        return timezone.now().weekday() < 5
