"""Steps that handle confirmation of commands in the Telegram bot."""

from collections.abc import Callable
from typing import TYPE_CHECKING

from apps.telegram.bot import Bot
from apps.telegram.bot.steps import Step

if TYPE_CHECKING:
    from apps.telegram.bot import TelegramUpdate
    from apps.telegram.bot.commands import Command


def prettyprint(data: dict):
    """Pretty print the provided dictionary."""
    return "\n".join([f"{k}={v}" for k, v in data.items()])


class Confirm(Step):
    """Represent the confirmation step in a Telegram bot command."""

    def __init__(
        self,
        command: "Command",
        steps_back: int = 0,
        unique_id: str | None = None,
        data_transform_func: Callable[[dict], str] = prettyprint,
    ):
        """Initialize the confirmation step."""
        self.data_transform_func = data_transform_func
        super().__init__(command, steps_back=steps_back, unique_id=unique_id)

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the confirmation step."""
        data = self.get_callback_data(telegram_update)
        data_confirmed = dict(data, confirmed=True)
        confirmation_yes = self.next_step_callback(**data_confirmed)
        data_declined = dict(data, confirmed=False)
        confirmation_no = self.cancel_callback(**data_declined)

        keyboard = [
            [{"text": "✅ Ok", "callback_data": confirmation_yes}],
            [{"text": "❌ Cancel", "callback_data": confirmation_no}],
        ]

        self.maybe_add_previous_button(keyboard, **data)

        message = f"{self.command.name} with the following data?\n{self.data_transform_func(data)}"
        Bot.send_message(
            message,
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )
