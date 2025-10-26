"""Register work command for the Telegram bot."""

from datetime import date

from apps.projects.models import Project
from apps.telegram.bot.commands.common import SelectDay, SelectWorkedHours
from apps.telegram.bot.commands.core import Command, Step
from apps.telegram.bot.core import Bot
from apps.timesheets.models import Timesheet


class RegisterWork(Command):
    """Represent the register work command."""

    command = "/registerwork"
    description = "Register working hours for a specific day on a specific project."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectMissingDay(self), SelectWorkedHours(self, steps_back=1), RegisterWorkedHours(self)]


class SelectMissingDay(SelectDay):
    """Represent the missing day selection step in a Telegram bot command."""

    def get_days(self):
        """Get the missing days for the settings' user's project."""
        draft_timesheets = Timesheet.objects.filter(status=Timesheet.Status.DRAFT, user=self.command.settings.user)
        missing = [(timesheet.project, date) for timesheet in draft_timesheets for date in timesheet.get_missing_days()]
        return sorted(missing, key=lambda x: x[1])

    def get_keyboard(self, days: list[tuple[Project, date]], data: dict, start: int, end: int):
        """Get the keyboard for the given days and data."""
        keyboard = []
        for project, day in days[start:end]:
            data_day = dict(data, start_date=day, project_id=project.pk, project_name=project.name)
            keyboard.append([{"text": f"{project}: {day}", "callback_data": self.next_step_callback(**data_day)}])
        return keyboard


class RegisterWorkedHours(Step):
    """Represent the registration of work step in a Telegram bot command."""

    def handle(self, telegram_update):
        """Confirm if the registraiton of work was successful or not."""
        data = self.get_callback_data(telegram_update)
        msg = self._try_registerwork(data)
        Bot.send_message(msg, self.command.settings.chat_id, message_id=telegram_update.message_id)

    def _try_registerwork(self, data: dict):
        try:
            self._registerwork(data)
        except Timesheet.DoesNotExist:
            # Could happen when a user is filling in working hours, but in the meantime the timesheet was completed.
            msg = (
                "The timesheet you are trying to register work for is in an invalid state. Contact your administrator."
            )
        else:
            msg = f"Successfully registered {data['duration']}h for {data['project_name']} on {data['start_date']}."
        return msg

    def _registerwork(self, data: dict):
        """Register work hours for the given date and option."""
        assert data["start_date"], "Start date must be set."
        start_date = date.fromisoformat(data["start_date"])
        timesheet = Timesheet.objects.get(
            status=Timesheet.Status.DRAFT,
            month=start_date.month,
            year=start_date.year,
            user=self.command.settings.user,
            project_id=data["project_id"],
        )
        timesheet.timesheetitem_set.create(date=start_date, worked_hours=data["duration"])
