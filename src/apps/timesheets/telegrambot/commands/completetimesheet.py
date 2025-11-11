"""Complete timesheet command for the Telegram bot."""

from django_telegram_app.bot.base import BaseCommand, Step

from apps.timesheets.telegrambot.steps import Confirm, MarkTimesheetAsCompleted, SelectTimesheet


class Command(BaseCommand):
    """Represent the complete timesheet command."""

    description = "Mark a timesheet as completed"

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectTimesheet(self), Confirm(self, steps_back=1), MarkTimesheetAsCompleted(self)]
