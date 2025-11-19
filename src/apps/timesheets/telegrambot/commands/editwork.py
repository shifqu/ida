"""Edit work command for the Telegram bot."""

from apps.telegram.telegrambot.base import TelegramCommand
from apps.timesheets.telegrambot.steps import EditWorkedHours, SelectExistingDay, SelectWorkedHours


class Command(TelegramCommand):
    """Represent the edit work command."""

    description = "Edit previously registered working hours"

    @property
    def steps(self):
        """Return the steps of the command."""
        return [SelectExistingDay(self), SelectWorkedHours(self, steps_back=1), EditWorkedHours(self)]
