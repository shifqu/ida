"""Register work command for the Telegram bot."""

from apps.telegram.telegrambot.base import TelegramCommand
from apps.timesheets.telegrambot.steps import RegisterWorkedHours, SelectMissingDay, SelectWorkedHours


class Command(TelegramCommand):
    """Represent the register work command."""

    description = "Register working hours for a specific day on a specific project."

    @property
    def steps(self):
        """Return the steps of the command."""
        return [SelectMissingDay(self), SelectWorkedHours(self, steps_back=1), RegisterWorkedHours(self)]
