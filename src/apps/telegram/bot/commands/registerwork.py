"""Register work command for the Telegram bot."""

from apps.telegram.bot.commands import Command
from apps.telegram.bot.steps import RegisterWorkedHours, SelectMissingDay, SelectWorkedHours, Step


class RegisterWork(Command):
    """Represent the register work command."""

    command = "/registerwork"
    description = "Register working hours for a specific day on a specific project."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectMissingDay(self), SelectWorkedHours(self, steps_back=1), RegisterWorkedHours(self)]
