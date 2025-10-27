"""Complete timesheet command for the Telegram bot."""

from apps.telegram.bot.commands import Command
from apps.telegram.bot.steps import Confirm, MarkTimesheetAsCompleted, SelectTimesheet, Step


class CompleteTimesheet(Command):
    """Represent the complete timesheet command."""

    command = "/completetimesheet"
    description = "Mark a timesheet as completed"

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectTimesheet(self), Confirm(self, steps_back=1), MarkTimesheetAsCompleted(self)]
