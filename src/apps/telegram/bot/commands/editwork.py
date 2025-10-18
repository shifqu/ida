"""Edit work command for the Telegram bot."""

from dataclasses import dataclass, replace
from datetime import date

from apps.telegram.bot.commands.base import Command, CommandData
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet, TimesheetItem


@dataclass
class WorkData(CommandData):
    """Represent the data for the edit work command."""

    project_id: int = 0
    project_name: str = ""
    start_date: date | None = None
    duration: int = 0
    current_page: int = 1
    item_pk: int = 0

    @classmethod
    def fromdict(cls, data: dict):
        """Create an instance from a dictionary."""
        instance = super().fromdict(data)
        if instance.start_date and isinstance(instance.start_date, str):
            instance.start_date = date.fromisoformat(instance.start_date)
        return instance


class EditWork(Command[WorkData]):
    """Represent the edit work command."""

    name = "/editwork"
    data_class = WorkData

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the edit work command."""
        self._select_day(telegram_update)

    def _select_day(self, telegram_update: TelegramUpdate):
        """Select the day of work that should be edited."""
        data = self.get_command_data(telegram_update.callback_data)

        start = (data.current_page - 1) * 4
        end = start + 4

        existing_days = self._get_existing_days()
        if not existing_days:
            msg = "No existing days found. Not possible to edit standard hours."
            return Bot.send_message(msg, telegram_update.chat_id)

        keyboard = []
        for project, item in existing_days[start:end]:
            data_day = replace(
                data, start_date=item.date, project_id=project.pk, project_name=project.name, item_pk=item.pk
            )
            keyboard.append(
                [
                    {
                        "text": f"{project}: {item.date} ({item.worked_hours}h)",
                        "callback_data": self.create_callback("_select_hours_worked", **data_day.asdict()),
                    }
                ]
            )

        if data.current_page > 1:
            data_back = replace(data, current_page=data.current_page - 1)
            keyboard.append(
                [{"text": "⬅️ Back", "callback_data": self.create_callback("_select_day", **data_back.asdict())}]
            )
        if len(existing_days) > end:
            data_next = replace(data, current_page=data.current_page + 1)
            keyboard.append(
                [{"text": "➡️ Next", "callback_data": self.create_callback("_select_day", **data_next.asdict())}]
            )

        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            "Select a day:", self.settings.chat_id, reply_markup=reply_markup, message_id=telegram_update.message_id
        )

    def _select_hours_worked(self, telegram_update: TelegramUpdate):
        """Show the options for the given day."""
        data = self.get_command_data(telegram_update.callback_data)
        options = {"Full day (8h)": 8, "Half day (4h)": 4, "Holiday (0h)": 0}
        keyboard = []
        for key, value in options.items():
            data_duration = replace(data, duration=value)
            keyboard.append([{"text": key, "callback_data": self.create_callback("finish", **data_duration.asdict())}])
        keyboard.append([{"text": "⬅️ Back", "callback_data": self.create_callback("_select_day", **data.asdict())}])
        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            f"Options for {data.start_date}:",
            self.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )

    def _finish_command(self, telegram_update: TelegramUpdate):
        """Confirm the editing of work hours."""
        data = self.get_command_data(telegram_update.callback_data)
        msg = self._try_editwork(data)
        Bot.send_message(msg, self.settings.chat_id, message_id=telegram_update.message_id)
        return data.correlation_key

    def _try_editwork(self, step_data: WorkData):
        try:
            self._editwork(step_data)
        except Timesheet.DoesNotExist:
            # Could happen when a user is filling in working hours, but in the meantime the timesheet was completed.
            msg = "The timesheet you are trying to edit work for is in an invalid state. Contact your administrator."
        else:
            msg = f"Successfully edited {step_data.duration}h for {step_data.project_name} on {step_data.start_date}."
        return msg

    def _get_existing_days(self):
        """Get the existing days for the settings' user's project.

        This is sorted by most recent date first.
        """
        draft_timesheets = Timesheet.objects.filter(status=Timesheet.Status.DRAFT, user=self.settings.user)
        existing = [
            (timesheet.project, item)
            for timesheet in draft_timesheets
            for item in timesheet.timesheetitem_set.filter(item_type=TimesheetItem.ItemType.STANDARD)
        ]
        return sorted(existing, key=lambda x: x[1].date, reverse=True)

    def _editwork(self, step_data: WorkData):
        """Edit working hours for the given date and option."""
        assert step_data.start_date, "Start date must be set."
        assert step_data.item_pk, "Item PK must be set."
        timesheet_item = TimesheetItem.objects.get(pk=step_data.item_pk, timesheet__status=Timesheet.Status.DRAFT)
        timesheet_item.worked_hours = step_data.duration
        timesheet_item.save()
