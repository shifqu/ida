"""Complete timesheet command for the Telegram bot."""

from dataclasses import dataclass

from apps.telegram.bot.commands.base import CommandDataWithConfirm, CommandWithConfirm
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet


@dataclass
class TimesheetData(CommandDataWithConfirm):
    """Represent the data for the confirm timesheet command."""

    timesheet_id: int | None = None
    timesheet_name: str | None = None


class CompleteTimesheet(CommandWithConfirm[TimesheetData]):
    """Represent the complete timesheet command."""

    name = "/completetimesheet"
    data_class = TimesheetData

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the command."""
        self._show_timesheet_selection(telegram_update)

    def _show_timesheet_selection(self, telegram_update: TelegramUpdate):
        """Show the timesheet selection for the command."""
        timesheets = Timesheet.objects.filter(user=self.settings.user, status=Timesheet.Status.DRAFT).order_by(
            "-year", "-month"
        )
        if not timesheets:
            Bot.send_message(
                "You have no timesheets to complete.",
                self.settings.chat_id,
                message_id=telegram_update.message_id,
            )
            return

        data = self.data_class()
        if len(timesheets) == 1:
            data.timesheet_id = timesheets[0].pk
            data.timesheet_name = str(timesheets[0])
            telegram_update.callback_data = self.create_callback("_handle_timesheet_selection", **data.asdict())
            return self._handle_timesheet_selection(telegram_update)

        keyboard = []
        for timesheet in timesheets:
            data.timesheet_id = timesheet.pk
            data.timesheet_name = str(timesheet)
            keyboard.append(
                [
                    {
                        "text": str(timesheet),
                        "callback_data": self.create_callback("_handle_timesheet_selection", **data.asdict()),
                    }
                ]
            )

        Bot.send_message(
            "Please select a timesheet to complete:",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_timesheet_selection(self, telegram_update: TelegramUpdate):
        step_data = self.get_command_data(telegram_update.callback_data)
        msg = f"Would you like to mark the following timesheet as completed:\n{step_data.timesheet_name}"
        self._show_confirmation(step_data, msg, telegram_update)

    def _finish_command(self, telegram_update: TelegramUpdate):
        step_data = self.get_command_data(telegram_update.callback_data)
        if step_data.confirmation:
            timesheet = Timesheet.objects.get(pk=step_data.timesheet_id)
            timesheet.mark_as_completed()
            msg = f"Successfully marked the timesheet {timesheet} as completed."
        else:
            msg = "Timesheet completion cancelled."

        Bot.send_message(
            msg,
            self.settings.chat_id,
            message_id=telegram_update.message_id,
        )
        return step_data.correlation_key
