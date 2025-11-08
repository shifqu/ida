"""Steps that wait for input in a Telegram bot command."""

from __future__ import annotations

from typing import TYPE_CHECKING

from apps.telegram.bot.base import Step
from apps.telegram.bot.bot import send_message

if TYPE_CHECKING:
    from apps.telegram.bot.base import BaseCommand, TelegramUpdate


class WaitForTime(Step):
    """Represent the wait for time input step in a Telegram bot command."""

    def __init__(self, command: BaseCommand, key: str, date_key: str, unique_id: str | None = None):
        """Initialize the wait for time input step."""
        self.key = key
        self.date_key = date_key
        super().__init__(command, steps_back=0, unique_id=unique_id)

    def handle(self, telegram_update: "TelegramUpdate"):
        """Prompt the user to input a time."""
        data = self.get_callback_data(telegram_update)
        self.add_waiting_for(self.key, data)
        send_message(
            f"Enter the {self.key} time (HH:MM) for {data[self.date_key]}:",
            self.command.settings.chat_id,
            message_id=telegram_update.message_id,
        )


class WaitForDescription(Step):
    """Represent the description selection step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Prompt the user to input a description or select no description."""
        data = self.get_callback_data(telegram_update)
        self.add_waiting_for("description", data)
        data_dict = dict(data, description="")
        keyboard = [[{"text": "No description.", "callback_data": self.next_step_callback(**data_dict)}]]
        send_message(
            "Send the description (or select 'No description'):",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )
