"""Complete timesheet command for the Telegram bot."""

from apps.telegram.bot.commands.common import Confirm, SelectTimesheet
from apps.telegram.bot.commands.core import Command, Step
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet


class CompleteTimesheet(Command):
    """Represent the complete timesheet command."""

    command = "/completetimesheet"
    description = "Mark a timesheet as completed"

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [SelectTimesheet(self), Confirm(self, steps_back=1), MarkTimesheetAsCompleted(self)]


class MarkTimesheetAsCompleted(Step):
    """Represent the step to mark the selected timesheet as completed."""

    def handle(self, telegram_update: TelegramUpdate):
        """Show the mark timesheet as completed step."""
        data = self.get_callback_data(telegram_update)
        timesheet = Timesheet.objects.get(pk=data["timesheet_id"])
        timesheet.mark_as_completed()

        Bot.send_message(
            f"Successfully marked the timesheet {timesheet} as completed.",
            self.command.settings.chat_id,
            message_id=telegram_update.message_id,
        )
        self.command.next_step(self.name, telegram_update)
