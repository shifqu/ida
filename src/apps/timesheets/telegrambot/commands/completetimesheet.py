"""Complete timesheet command for the Telegram bot."""

from apps.telegram.telegrambot.base import TelegramCommand
from apps.timesheets.telegrambot.steps import Confirm, MarkTimesheetAsCompleted, SelectTimesheet


class Command(TelegramCommand):
    """Represent the complete timesheet command."""

    description = "Mark a timesheet as completed"

    @property
    def steps(self):
        """Return the steps of the command."""
        return [SelectTimesheet(self), Confirm(self, steps_back=1), MarkTimesheetAsCompleted(self)]
