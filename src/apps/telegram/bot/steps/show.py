"""Steps that show data in a Telegram bot command."""

from typing import TYPE_CHECKING

from apps.telegram.bot import Bot
from apps.telegram.bot.steps import Step
from apps.telegram.bot.steps._types import OverviewType
from apps.timesheets.models import Timesheet

if TYPE_CHECKING:
    from apps.telegram.bot import TelegramUpdate


class ShowOverview(Step):
    """Represent the show overview step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the overview to the user."""
        step_data = self.get_callback_data(telegram_update)
        timesheet_id = step_data["timesheet_id"]
        overview_type = step_data["overview_type"]

        try:
            timesheet = Timesheet.objects.get(pk=timesheet_id, user=self.command.settings.user)
        except Timesheet.DoesNotExist:
            error_message = "The selected timesheet does not exist."
            Bot.send_message(error_message, self.command.settings.chat_id, message_id=telegram_update.message_id)
            return self.command.finish(self.name, telegram_update)

        if overview_type == OverviewType.HOLIDAYS.value:
            overview_text = timesheet.get_holidays_overview()
        elif overview_type == OverviewType.SUMMARY.value:
            overview_text = timesheet.get_overview(include_details=False)
        elif overview_type == OverviewType.DETAILED.value:
            overview_text = timesheet.get_overview(include_details=True)
        else:
            error_message = "Invalid overview type selected."
            Bot.send_message(error_message, self.command.settings.chat_id, message_id=telegram_update.message_id)
            return self.command.finish(self.name, telegram_update)

        Bot.send_message(overview_text, self.command.settings.chat_id, message_id=telegram_update.message_id)
        self.command.next_step(self.name, telegram_update)
