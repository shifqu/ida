"""Request Overview command for the Telegram bot."""

import enum
import logging

from apps.telegram.bot.commands.common import SelectTimesheet
from apps.telegram.bot.commands.core import Command, Step
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet


class RequestOverview(Command):
    """Represent the request overview command."""

    command = "/requestoverview"
    description = "Request an overview of a timesheet and its items."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [
            SelectTimesheet(self, filter_kwargs={"user": self.settings.user}),
            SelectOverviewType(self, allow_previous=True),
            ShowOverview(self, allow_previous=True),
        ]


class OverviewType(enum.Enum):
    """Enumeration for overview types."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    HOLIDAYS = "holidays"


class SelectOverviewType(Step):
    """Represent the overview type selection step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
        """Show the overview type selection to the user."""
        logging.info(f"Handling {self.name} step for user {self.command.settings.user}: {telegram_update}")
        data = self.get_callback_data(telegram_update)
        keyboard = [
            [
                {
                    "text": "Summary Overview",
                    "callback_data": self.next_step_callback(**data, overview_type=OverviewType.SUMMARY.value),
                }
            ],
            [
                {
                    "text": "Detailed Overview",
                    "callback_data": self.next_step_callback(**data, overview_type=OverviewType.DETAILED.value),
                }
            ],
            [
                {
                    "text": "Holidays Overview",
                    "callback_data": self.next_step_callback(**data, overview_type=OverviewType.HOLIDAYS.value),
                }
            ],
        ]
        self.maybe_add_previous_button(keyboard, **data)

        Bot.send_message(
            "Which type of overview would you like to see?",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class ShowOverview(Step):
    """Represent the show overview step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
        """Show the overview to the user."""
        logging.info(f"Handling {self.name} step for user {self.command.settings.user}: {telegram_update}")
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
