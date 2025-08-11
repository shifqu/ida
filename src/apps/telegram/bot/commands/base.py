"""Base command for the Telegram bot."""

from apps.telegram.models import TelegramSettings
from apps.telegram.types import TelegramUpdate


class Command:
    """Represent a base command class."""

    name: str

    def __init__(self, settings: TelegramSettings):
        """Initialize the command with the given settings."""
        self.settings = settings

    def start(self, telegram_update: TelegramUpdate):
        """Start the command with the given Telegram update."""
        self.clear_state()
        self._start_command(telegram_update)

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the command logic."""
        raise NotImplementedError("Subclasses must implement this method")

    def clear_state(self):
        """Clear the command state."""
        self.settings.data = {}
        self.settings.save()
