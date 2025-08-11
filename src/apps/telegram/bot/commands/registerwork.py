"""Register work command for the Telegram bot."""

from datetime import datetime

from apps.telegram.bot.commands.base import Command
from apps.telegram.bot.core import Bot
from apps.telegram.types import TelegramUpdate
from apps.timesheets.models import Timesheet


class RegisterWork(Command):
    """Represent the register work command.

    TODO: Warn on duplicate registrations.
    """

    name = "/registerwork"

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the register work command."""
        self.select_day(telegram_update)

    def select_day(self, telegram_update: TelegramUpdate):
        """Select the day for registering work."""
        page = 1
        if telegram_update.callback_data:
            page = int(telegram_update.callback_data.split("|")[-1])

        start = (page - 1) * 4
        end = start + 4

        missing_days = self._get_missing_days()
        if not missing_days:
            msg = "No missing days found. No need to register standard hours today."
            return Bot.send_message(msg, telegram_update.chat_id)

        keyboard = [
            [{"text": day, "callback_data": f"{self.name}|select_hours_worked|{day}|{page}"}]
            for day in missing_days[start:end]
        ]

        if page > 1:
            keyboard.append([{"text": "⬅️ Back", "callback_data": f"{self.name}|select_day|{page - 1}"}])
        if len(missing_days) > end:
            keyboard.append([{"text": "➡️ Next", "callback_data": f"{self.name}|select_day|{page + 1}"}])

        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            "Select a day:", self.settings.chat_id, reply_markup=reply_markup, message_id=telegram_update.message_id
        )

    def select_hours_worked(self, telegram_update: TelegramUpdate):
        """Show the options for the given day."""
        _command, _step, date_str, current_page = telegram_update.callback_data.split("|")
        options = ["0h", "4h", "8h", "16h", "24h"]
        keyboard = [
            [{"text": option, "callback_data": f"{self.name}|confirm_registration|{date_str}|{option}"}]
            for option in options
        ]
        keyboard.append([{"text": "⬅️ Back", "callback_data": f"{self.name}|select_day|{current_page}"}])
        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            f"Options for {date_str}:",
            self.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )

    def confirm_registration(self, telegram_update: TelegramUpdate):
        """Confirm the registration of work hours."""
        _command, _step, date_str, option = telegram_update.callback_data.split("|")
        self._registerwork(date_str, option)
        Bot.send_message(
            f"{date_str}: {option} registered.", self.settings.chat_id, message_id=telegram_update.message_id
        )

    def _get_missing_days(self):
        """Get the missing days for the settings' user."""
        draft_timesheets = Timesheet.objects.filter(status=Timesheet.Status.DRAFT, user=self.settings.user)
        return [str(date) for timesheet in draft_timesheets for date in timesheet.get_missing_days()]

    def _registerwork(self, date_str: str, option: str):
        """Register work hours for the given date and option."""
        hours = option.lower().replace("h", "")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        timesheet = Timesheet.objects.get(
            status=Timesheet.Status.DRAFT, month=date_obj.month, year=date_obj.year, user=self.settings.user
        )
        timesheet.timesheetitem_set.create(date=date_str, worked_hours=hours)
