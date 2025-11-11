"""Edit work command for the Telegram bot."""

from django_telegram_app.bot.base import BaseCommand, Step

from apps.timesheets.telegrambot.steps import EditWorkedHours, SelectExistingDay, SelectWorkedHours


class Command(BaseCommand):
    """Represent the edit work command."""

    description = "Edit previously registered working hours"

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectExistingDay(self), SelectWorkedHours(self, steps_back=1), EditWorkedHours(self)]
