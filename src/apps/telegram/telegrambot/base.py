"""Base telegram settings."""

from abc import ABC

from django_telegram_app.bot.base import BaseBotCommand, Step

from apps.telegram.models import TelegramSettings


class TelegramCommand(BaseBotCommand, ABC):
    """Project specific base class for telegram commands."""

    settings: TelegramSettings


class TelegramStep(Step, ABC):
    """Project specific base class for telegram command steps."""

    command: TelegramCommand

    def __init__(self, command: TelegramCommand, unique_id: str | None = None, steps_back: int = 0):
        """Initialize the telegram step.

        Steps back is configured on the step level since we re-use steps in multiple commands, so the amount of
        steps to go back might differ depending on the command.
        """
        self.steps_back = steps_back
        super().__init__(command, unique_id)

    def maybe_add_previous_button(self, keyboard: list[list[dict]], data: dict, **kwargs):
        """Add a previous button if steps_back is set."""
        if self.steps_back <= 0:
            return
        keyboard.append(
            [
                {
                    "text": "⬅️ Previous step",
                    "callback_data": self.previous_step_callback(
                        steps_back=self.steps_back, original_data=data, **kwargs
                    ),
                }
            ]
        )
