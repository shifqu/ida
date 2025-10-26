"""Edit work command for the Telegram bot."""

from apps.projects.models import Project
from apps.telegram.bot.commands.common import SelectDay, SelectWorkedHours
from apps.telegram.bot.commands.core import Command, Step
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet, TimesheetItem


class EditWork(Command):
    """Represent the edit work command."""

    command = "/editwork"
    description = "Edit previously registered working hours"

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectExistingDay(self), SelectWorkedHours(self, steps_back=1), EditWorkedHours(self)]


class SelectExistingDay(SelectDay):
    """Represent the existing day selection step in a Telegram bot command."""

    def get_days(self):
        """Get the existing days for the settings' user's project.

        This is sorted by most recent date first.
        """
        draft_timesheets = Timesheet.objects.filter(status=Timesheet.Status.DRAFT, user=self.command.settings.user)
        existing = [
            (timesheet.project, item)
            for timesheet in draft_timesheets
            for item in timesheet.timesheetitem_set.filter(item_type=TimesheetItem.ItemType.STANDARD)
        ]
        return sorted(existing, key=lambda x: x[1].date, reverse=True)

    def get_keyboard(self, days: list[tuple[Project, TimesheetItem]], data: dict, start: int, end: int):
        """Get the keyboard for the given days and data."""
        keyboard = []
        for project, item in days[start:end]:
            data_day = dict(
                data, start_date=item.date, project_id=project.pk, project_name=project.name, item_pk=item.pk
            )
            keyboard.append(
                [
                    {
                        "text": f"{project}: {item.date} ({item.worked_hours}h)",
                        "callback_data": self.next_step_callback(**data_day),
                    }
                ]
            )
        return keyboard


class EditWorkedHours(Step):
    """Represent the editing of work step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
        """Confirm if the editing of work was successful or not."""
        data = self.get_callback_data(telegram_update)
        msg = self._try_editwork(data)
        Bot.send_message(msg, self.command.settings.chat_id, message_id=telegram_update.message_id)
        return self.command.next_step(self.name, telegram_update)

    def _try_editwork(self, data: dict):
        try:
            self._editwork(data)
        except Timesheet.DoesNotExist:
            # Could happen when a user is filling in working hours, but in the meantime the timesheet was completed.
            msg = "The timesheet you are trying to edit work for is in an invalid state. Contact your administrator."
        else:
            msg = f"Successfully edited {data['duration']}h for {data['project_name']} on {data['start_date']}."
        return msg

    def _editwork(self, data: dict):
        """Edit working hours for the given date and option."""
        timesheet_item = TimesheetItem.objects.get(pk=data["item_pk"], timesheet__status=Timesheet.Status.DRAFT)
        timesheet_item.worked_hours = data["duration"]
        timesheet_item.save()
