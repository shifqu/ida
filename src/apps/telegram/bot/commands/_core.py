"""Core classes and functions for Telegram bot commands."""

import logging
import uuid
from typing import TYPE_CHECKING, Any

from apps.telegram.models import CallbackData

if TYPE_CHECKING:
    from apps.telegram.bot import TelegramUpdate
    from apps.telegram.bot.steps import Step
    from apps.telegram.models import AbstractTelegramSettings


class Command:
    """Represent a Telegram bot command."""

    command: str
    description: str

    @property
    def steps(self) -> list["Step"]:
        """Return the steps of the command."""
        raise NotImplementedError("Subclasses must implement this method")

    def __init__(self, settings: "AbstractTelegramSettings"):
        """Initialize the command."""
        self.settings = settings

    def start(self, telegram_update: "TelegramUpdate"):
        """Start the command."""
        logging.info(f"Starting {self.name} for user {self.settings.user}")
        self._clear_state()
        return self.steps[0].handle(telegram_update)

    def finish(self, current_step_name: str, telegram_update: "TelegramUpdate"):
        """Finish the command and clear all data."""
        logging.info(f"Finishing the command at step {current_step_name}")
        self._clear_state()
        self._clear_callback_data(telegram_update)

    def cancel(self, current_step_name: str, telegram_update: "TelegramUpdate"):
        """Cancel the command and clear all data."""
        from apps.telegram.bot import Bot

        Bot.send_message("Command canceled", self.settings.chat_id)
        return self.finish(current_step_name, telegram_update)

    def next_step(self, current_step_name: str, telegram_update: "TelegramUpdate"):
        """Proceed to the next step in the command."""
        next_index = self._steps_to_str().index(current_step_name) + 1
        if next_index < len(self.steps):
            next_step = self.steps[next_index]
            return next_step.handle(telegram_update)
        self.finish(current_step_name, telegram_update)

    def previous_step(self, current_step_name: str, telegram_update: "TelegramUpdate"):
        """Return to the previous step in the command."""
        data = self.get_callback_data(telegram_update.callback_data)
        steps_back = int(data.get("_steps_back", 1))
        previous_index = self._steps_to_str().index(current_step_name) - steps_back
        if previous_index >= 0:
            previous_step = self.steps[previous_index]
            return previous_step.handle(telegram_update)

    def current_step(self, current_step_name: str, telegram_update: "TelegramUpdate"):
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

    def _clear_callback_data(self, telegram_update: "TelegramUpdate"):
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


def get_command_list() -> list[type["Command"]]:
    """Return the list of available command classes."""
    from apps.telegram.bot.commands.completetimesheet import CompleteTimesheet
    from apps.telegram.bot.commands.editwork import EditWork
    from apps.telegram.bot.commands.registerovertime import RegisterOvertime
    from apps.telegram.bot.commands.registerwork import RegisterWork
    from apps.telegram.bot.commands.requestoverview import RequestOverview

    return [
        RegisterWork,
        RegisterOvertime,
        CompleteTimesheet,
        EditWork,
        RequestOverview,
    ]


def get_command_cls(name: str):
    """Return the command class based on the name."""
    command_map = {cmd.command: cmd for cmd in get_command_list()}
    return command_map[name]
