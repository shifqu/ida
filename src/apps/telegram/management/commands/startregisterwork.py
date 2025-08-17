"""Django command to start a RegisterWork command for active users with a chat_id."""

from apps.telegram.management.commands.base import TelegramCommand


class Command(TelegramCommand):
    """Start a RegisterWork command."""

    help = "Start a RegisterWork command to let users register their work hours."
    command_text = "/registerwork"
