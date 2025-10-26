"""Core classes and functions for Telegram bot commands."""

import logging
import uuid
from typing import Any

from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.telegram.models import CallbackData, TelegramSettings


class Command:
    """Represent a Telegram bot command."""

    command: str
    description: str

    @property
    def steps(self) -> list["Step"]:
        """Return the steps of the command."""
        raise NotImplementedError("Subclasses must implement this method")

    def __init__(self, settings: TelegramSettings):
        """Initialize the command."""
        self.settings = settings

    def start(self, telegram_update: TelegramUpdate):
        """Start the command."""
        logging.info(f"Starting {self.name} for user {self.settings.user}")
        self._clear_state()
        return self.steps[0].handle(telegram_update)

    def finish(self, current_step_name: str, telegram_update: TelegramUpdate):
        """Finish the command and clear all data."""
        logging.info(f"Finishing the command at step {current_step_name}")
        self._clear_state()
        self._clear_callback_data(telegram_update)

    def cancel(self, current_step_name: str, telegram_update: TelegramUpdate):
        """Cancel the command and clear all data."""
        Bot.send_message("Command canceled", self.settings.chat_id)
        return self.finish(current_step_name, telegram_update)

    def next_step(self, current_step_name: str, telegram_update: TelegramUpdate):
        """Proceed to the next step in the command."""
        next_index = self._steps_to_str().index(current_step_name) + 1
        if next_index < len(self.steps):
            next_step = self.steps[next_index]
            return next_step.handle(telegram_update)
        self.finish(current_step_name, telegram_update)

    def previous_step(self, current_step_name: str, telegram_update: TelegramUpdate):
        """Return to the previous step in the command."""
        data = self.get_callback_data(telegram_update.callback_data)
        steps_back = int(data.get("_steps_back", 1))
        previous_index = self._steps_to_str().index(current_step_name) - steps_back
        if previous_index >= 0:
            previous_step = self.steps[previous_index]
            return previous_step.handle(telegram_update)

    def current_step(self, current_step_name: str, telegram_update: TelegramUpdate):
        """Reload the current step."""
        current_index = self._steps_to_str().index(current_step_name)
        current_step = self.steps[current_index]
        return current_step.handle(telegram_update)

    def create_callback(self, step_name: str, action: str, **kwargs):
        """Create callback data for the current command and return the token."""
        callback_data = CallbackData(command=self.command, step=step_name, action=action, data=kwargs)
        callback_data.save()
        return str(callback_data.token)

    def get_callback(self, token: str):
        """Return the callback for the given token."""
        return CallbackData.objects.get(token=token)

    def get_callback_data(self, callback_token: str) -> dict[str, Any]:
        """Get callback data from the callback token.

        If the callback token is not provided, return an empty dictionary.
        """
        if not callback_token:
            return self._get_default_callback_data()
        callback_data = self.get_callback(callback_token)
        return callback_data.data

    def _get_default_callback_data(self):
        """Return a dictionary with correlation key as default callback data."""
        return {"correlation_key": str(uuid.uuid4())}

    def _clear_state(self):
        """Clear the command state."""
        self.settings.data = {}
        self.settings.save()

    def _clear_callback_data(self, telegram_update: TelegramUpdate):
        """Clear callback data for the current command."""
        step_data = self.get_callback_data(telegram_update.callback_data)
        correlation_key = step_data["correlation_key"]
        if not correlation_key:
            return
        CallbackData.objects.filter(data__correlation_key=correlation_key).delete()

    def _steps_to_str(self):
        return [step.name for step in self.steps]

    @property
    def name(self):
        """Return the name of the command."""
        return type(self).__name__


class Step:
    """Represent a step in a Telegram bot command."""

    def __init__(self, command: Command, steps_back: int = 0, unique_id: str | None = None):
        """Initialize the step."""
        self.command = command
        self.steps_back = steps_back
        self.unique_id = unique_id

    def handle(self, telegram_update: TelegramUpdate):
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

    def get_callback_data(self, telegram_update: TelegramUpdate) -> dict[str, Any]:
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
