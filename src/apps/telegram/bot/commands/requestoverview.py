"""Request Overview command for the Telegram bot."""

from apps.telegram.bot.commands import Command
from apps.telegram.bot.steps import SelectOverviewType, SelectTimesheet, ShowOverview, Step


class RequestOverview(Command):
    """Represent the request overview command."""

    command = "/requestoverview"
    description = "Request an overview of a timesheet and its items."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [
            SelectTimesheet(self, filter_kwargs={"user": self.settings.user}),
            SelectOverviewType(self, steps_back=1),
            ShowOverview(self, steps_back=1),
        ]
