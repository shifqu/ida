"""Django command to start a RegisterWork command for active users with a chat_id."""

from django.utils import timezone
from django_telegram_app.management.base import BaseTelegramCommand


class Command(BaseTelegramCommand):
    """Start a RegisterWork command."""

    help = "Start a RegisterWork command to let users register their work hours."
    command_text = "/registerwork"

    def should_run(self):
        """Only run on weekdays."""
        return timezone.now().weekday() < 5
