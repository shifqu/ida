"""Base command for the Telegram bot."""

from dataclasses import asdict, dataclass, field
from typing import Generic, TypeVar

from apps.telegram.bot.commands.utils import generate_correlation_key
from apps.telegram.bot.types import TelegramUpdate
from apps.telegram.models import CallbackData, TelegramSettings


@dataclass
class CommandData:
    """Represent the data for a telegram command.

    This class is supposed to be subclassed by each specific command data class.
    """

    correlation_key: str = field(default_factory=generate_correlation_key)

    @classmethod
    def fromdict(cls, data: dict):
        """Create an instance from a dictionary."""
        return cls(**data)

    def asdict(self):
        """Convert the instance to a dictionary."""
        return asdict(self)


T = TypeVar("T", bound=CommandData)


class Command(Generic[T]):
    """Represent a base Telegram command class."""

    name: str
    data_class: type[T]

    def __init__(self, settings: TelegramSettings):
        """Initialize the command with the given settings."""
        self.settings = settings

    def start(self, telegram_update: TelegramUpdate):
        """Start the command with the given Telegram update."""
        self.clear_state()
        self._start_command(telegram_update)

    def _start_command(self, telegram_update: TelegramUpdate) -> None:
        """Start the command logic."""
        raise NotImplementedError("Subclasses must implement this method")

    def clear_state(self):
        """Clear the command state."""
        self.settings.data = {}
        self.settings.save()

    def clear_callback_data(self, correlation_key: str):
        """Clear callback data for the current command."""
        if not correlation_key:
            return
        CallbackData.objects.filter(data__correlation_key=correlation_key).delete()

    def finish(self, telegram_update: TelegramUpdate):
        """Finish the command and clear all data."""
        correlation_key = self._finish_command(telegram_update)
        self.clear_state()
        self.clear_callback_data(correlation_key)

    def _finish_command(self, telegram_update: TelegramUpdate) -> str:
        """Run the last step of the command and return the correlation key."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_callback(self, token: str):
        """Return the callback for the given token."""
        return CallbackData.objects.get(token=token)

    def create_callback(self, step_name: str, **kwargs):
        """Create callback data for the current command and return the token."""
        callback_data = CallbackData(command=self.name, step=step_name, data=kwargs)
        callback_data.save()
        return str(callback_data.token)

    def get_command_data(self, callback_token: str):
        """Get command data from the callback token.

        If the callback token is not provided, return a new instance of the data class.
        """
        if not callback_token:
            return self.data_class()
        callback_data = self.get_callback(callback_token)
        return self.data_class.fromdict(callback_data.data)
