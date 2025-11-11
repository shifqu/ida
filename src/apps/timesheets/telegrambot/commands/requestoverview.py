"""Request Overview command for the Telegram bot."""

from django_telegram_app.bot.base import BaseCommand, Step

from apps.timesheets.telegrambot.steps import SelectOverviewType, SelectTimesheet, ShowOverview


class Command(BaseCommand):
    """Represent the request overview command."""

    description = "Request an overview of a timesheet and its items."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [
            SelectTimesheet(self, filter_kwargs={"user": self.settings.user}),
            SelectOverviewType(self, steps_back=1),
            ShowOverview(self, steps_back=1),
        ]
