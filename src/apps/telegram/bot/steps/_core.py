"""Core classes and functions for Telegram bot steps."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.telegram.bot import TelegramUpdate
    from apps.telegram.bot.commands import Command


class Step:
    """Represent a step in a Telegram bot command."""

    def __init__(self, command: "Command", steps_back: int = 0, unique_id: str | None = None):
        """Initialize the step."""
        self.command = command
        self.steps_back = steps_back
        self.unique_id = unique_id

    def handle(self, telegram_update: "TelegramUpdate"):
        """Handle the step."""
        raise NotImplementedError("This method should be overridden by subclasses.")

    def next_step_callback(self, **kwargs):
        """Create a callback to advance to the next step."""
        return self._create_callback("next_step", **kwargs)

    def previous_step_callback(self, **kwargs):
        """Create a callback to return to the previous step."""
        return self._create_callback("previous_step", **kwargs)

    def current_step_callback(self, **kwargs):
        """Create a callback to reload the current step with the provided data."""
        return self._create_callback("current_step", **kwargs)

    def finish_callback(self, **kwargs):
        """Create a callback to finish the command."""
        return self._create_callback("finish", **kwargs)

    def cancel_callback(self, **kwargs):
        """Create a callback to cancel the command."""
        return self._create_callback("cancel", **kwargs)

    def maybe_add_previous_button(self, keyboard: list, **data):
        """Add a previous button to the provided keyboard if allowed."""
        if not self.steps_back:
            return
        data["_steps_back"] = self.steps_back
        keyboard.append([{"text": "⬅️ Previous step", "callback_data": self.previous_step_callback(**data)}])

    def get_callback_data(self, telegram_update: "TelegramUpdate") -> dict[str, Any]:
        """Get callback data from the telegram_update.

        If the update is a message and not a command, check if we are waiting for user input.
        If so, retrieve the callback data using the waiting_for token and store the message text
        in the appropriate key in the callback data.

        Otherwise, retrieve the callback data using the callback token from the update.
        If no callback token is provided, return an empty dictionary.
        """
        if not telegram_update.callback_data and telegram_update.is_message() and not telegram_update.is_command():
            waiting_for = self.command.settings.data.get("_waiting_for", None)
            if waiting_for:
                callback_token = waiting_for
                callback_data = self.command.get_callback_data(callback_token)
                key = callback_data["_message_key"]  # Move the message_text to this key
                callback_data[key] = telegram_update.message_text.strip()
                return callback_data

        callback_token = telegram_update.callback_data
        return self.command.get_callback_data(callback_token)

    def add_waiting_for(self, message_key: str, data: dict[str, Any]):
        """Add waiting_for to the command settings.

        The message_key will be used to store the user input in the callback data of the next step.
        """
        data["_message_key"] = message_key
        self.command.settings.data["_waiting_for"] = self.next_step_callback(**data)
        self.command.settings.save()

    @property
    def name(self):
        """Return the name of the step."""
        return self.unique_id or type(self).__name__

    def _create_callback(self, action, **kwargs):
        """Create callback data for the current step and return the token."""
        return self.command.create_callback(self.name, action, **kwargs)
