"""Edit work command for the Telegram bot."""

from apps.telegram.bot.commands import Command
from apps.telegram.bot.steps import EditWorkedHours, SelectExistingDay, SelectWorkedHours, Step


class EditWork(Command):
    """Represent the edit work command."""

    command = "/editwork"
    description = "Edit previously registered working hours"

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectExistingDay(self), SelectWorkedHours(self, steps_back=1), EditWorkedHours(self)]
