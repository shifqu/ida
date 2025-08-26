"""Django command to start the CompleteTimesheet command for active users with a chat_id."""

from apps.telegram.management.commands.base import TelegramCommand


class Command(TelegramCommand):
    """Start the CompleteTimesheet command."""

    help = "Start the CompleteTimesheet command to let users complete their timesheets."
    command_text = "/completetimesheet"
