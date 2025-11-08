"""Register work command for the Telegram bot."""

from apps.telegram.bot.base import BaseCommand, Step
from apps.timesheets.telegrambot.steps import RegisterWorkedHours, SelectMissingDay, SelectWorkedHours


class Command(BaseCommand):
    """Represent the register work command."""

    description = "Register working hours for a specific day on a specific project."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectMissingDay(self), SelectWorkedHours(self, steps_back=1), RegisterWorkedHours(self)]
