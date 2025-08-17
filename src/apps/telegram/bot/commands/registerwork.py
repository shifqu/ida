"""Register work command for the Telegram bot."""

from dataclasses import dataclass, replace
from datetime import date

from apps.telegram.bot.commands.base import Command, CommandData
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet


@dataclass
class WorkData(CommandData):
    """Represent the data for the register work command."""

    project_id: int = 0
    project_name: str = ""
    start_date: date | None = None
    duration: int = 0
    current_page: int = 1

    @classmethod
    def fromdict(cls, data: dict):
        """Create an instance from a dictionary."""
        instance = super().fromdict(data)
        if instance.start_date and isinstance(instance.start_date, str):
            instance.start_date = date.fromisoformat(instance.start_date)
        return instance


class RegisterWork(Command[WorkData]):
    """Represent the register work command."""

    name = "/registerwork"
    data_class = WorkData

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the register work command."""
        self._select_day(telegram_update)

    def _select_day(self, telegram_update: TelegramUpdate):
        """Select the day for registering work."""
        data = self.get_command_data(telegram_update.callback_data)

        start = (data.current_page - 1) * 4
        end = start + 4

        missing_days = self._get_missing_days()
        if not missing_days:
            msg = "No missing days found. No need to register standard hours today."
            return Bot.send_message(msg, telegram_update.chat_id)

        keyboard = []
        for project, day in missing_days[start:end]:
            data_day = replace(data, start_date=day, project_id=project.pk, project_name=project.name)
            keyboard.append(
                [
                    {
                        "text": f"{project}: {day}",
                        "callback_data": self.create_callback("_select_hours_worked", **data_day.asdict()),
                    }
                ]
            )

        if data.current_page > 1:
            data_back = replace(data, current_page=data.current_page - 1)
            keyboard.append(
                [{"text": "⬅️ Back", "callback_data": self.create_callback("_select_day", **data_back.asdict())}]
            )
        if len(missing_days) > end:
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
        """Confirm the registration of work hours."""
        data = self.get_command_data(telegram_update.callback_data)
        msg = self._try_registerwork(data)
        Bot.send_message(msg, self.settings.chat_id, message_id=telegram_update.message_id)
        return data.correlation_key

    def _try_registerwork(self, step_data: WorkData):
        try:
            self._registerwork(step_data)
        except Timesheet.DoesNotExist:
            # Could happen when a user is filling in working hours, but in the meantime the timesheet was completed.
            msg = (
                "The timesheet you are trying to register work for is in an invalid state. Contact your administrator."
            )
        else:
            msg = (
                f"Successfully registered {step_data.duration}h for {step_data.project_name} on {step_data.start_date}."
            )
        return msg

    def _get_missing_days(self):
        """Get the missing days for the settings' user's project."""
        draft_timesheets = Timesheet.objects.filter(status=Timesheet.Status.DRAFT, user=self.settings.user)
        missing = [(timesheet.project, date) for timesheet in draft_timesheets for date in timesheet.get_missing_days()]
        return sorted(missing, key=lambda x: x[1])

    def _registerwork(self, step_data: WorkData):
        """Register work hours for the given date and option."""
        assert step_data.start_date, "Start date must be set."
        timesheet = Timesheet.objects.get(
            status=Timesheet.Status.DRAFT,
            month=step_data.start_date.month,
            year=step_data.start_date.year,
            user=self.settings.user,
            project_id=step_data.project_id,
        )
        timesheet.timesheetitem_set.create(date=step_data.start_date, worked_hours=step_data.duration)
