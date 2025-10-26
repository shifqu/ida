"""Common functionality for the Telegram bot."""

import logging
from collections.abc import Callable

from apps.telegram.bot.commands.core import Command, Step
from apps.telegram.bot.commands.utils import prettyprint
from apps.telegram.bot.core import Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.timesheets.models import Timesheet


class SelectTimesheet(Step):
    """Represent the timesheet selection step in a Telegram bot command."""

    def __init__(
        self,
        command: Command,
        steps_back: int = 0,
        filter_kwargs: dict | None = None,
        order_by: tuple | None = None,
        unique_id: str | None = None,
    ):
        """Initialize the timesheet selection step."""
        self.filter_kwargs = filter_kwargs or dict(user=command.settings.user, status=Timesheet.Status.DRAFT)
        self.order_by = order_by or ("-year", "-month")
        super().__init__(command, steps_back=steps_back, unique_id=unique_id)

    def handle(self, telegram_update: TelegramUpdate):
        """Show the timesheet selection to the user."""
        logging.info(f"Handling {self.name} step for user {self.command.settings.user}")
        timesheets = Timesheet.objects.filter(**self.filter_kwargs).order_by(*self.order_by)
        if not timesheets:
            error_message = "No timesheets found."
            Bot.send_message(error_message, self.command.settings.chat_id, message_id=telegram_update.message_id)
            return self.command.finish(self.name, telegram_update)

        data = self.get_callback_data(telegram_update)
        if len(timesheets) == 1:
            data["timesheet_id"] = timesheets[0].pk
            data["timesheet_name"] = str(timesheets[0])
            telegram_update.callback_data = self.next_step_callback(**data)
            return self.command.next_step(self.name, telegram_update)

        keyboard = []
        for timesheet in timesheets:
            data["timesheet_id"] = timesheet.pk
            data["timesheet_name"] = str(timesheet)
            keyboard.append([{"text": str(timesheet), "callback_data": self.next_step_callback(**data)}])

        self.maybe_add_previous_button(keyboard, **data)

        Bot.send_message(
            "Select a timesheet:",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class Confirm(Step):
    """Represent the confirmation step in a Telegram bot command."""

    def __init__(
        self,
        command: Command,
        steps_back: int = 0,
        unique_id: str | None = None,
        data_transform_func: Callable[[dict], str] = prettyprint,
    ):
        """Initialize the confirmation step."""
        self.data_transform_func = data_transform_func
        super().__init__(command, steps_back=steps_back, unique_id=unique_id)

    def handle(self, telegram_update: TelegramUpdate):
        """Show the confirmation step."""
        data = self.get_callback_data(telegram_update)
        data_confirmed = dict(data, confirmed=True)
        confirmation_yes = self.next_step_callback(**data_confirmed)
        data_declined = dict(data, confirmed=False)
        confirmation_no = self.cancel_callback(**data_declined)

        keyboard = [
            [{"text": "✅ Ok", "callback_data": confirmation_yes}],
            [{"text": "❌ Cancel", "callback_data": confirmation_no}],
        ]

        self.maybe_add_previous_button(keyboard, **data)

        message = f"{self.command.name} with the following data?\n{self.data_transform_func(data)}"
        Bot.send_message(
            message,
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class SelectDay(Step):
    """Represent the day selection step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
        """Show the day selection to the user."""
        days = self.get_days()
        if not days:
            msg = f"No days found. Unable to complete {self.command.name}."
            Bot.send_message(msg, telegram_update.chat_id)
            return self.command.finish(self.name, telegram_update)

        data = self.get_callback_data(telegram_update)
        current_page: int = data.get("current_page", 1)
        start = (current_page - 1) * 4
        end = start + 4

        keyboard = self.get_keyboard(days, data, start, end)

        self._maybe_add_pagination_buttons(keyboard, days, data, current_page, end)

        self.maybe_add_previous_button(keyboard, **data)

        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            "Select a day:",
            self.command.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )

    def get_days(self):
        """Get the days to be displayed."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_keyboard(self, days: list[tuple], data: dict, start: int, end: int):
        """Get the keyboard for the given days and data."""
        raise NotImplementedError("Subclasses must implement this method")

    def _maybe_add_pagination_buttons(self, keyboard: list, days: list, data: dict, current_page: int, end: int):
        if current_page > 1:
            data_back = dict(data, current_page=current_page - 1)
            keyboard.append([{"text": "⬅️ Back", "callback_data": self.current_step_callback(**data_back)}])
        if len(days) > end:
            data_next = dict(data, current_page=current_page + 1)
            keyboard.append([{"text": "➡️ Next", "callback_data": self.current_step_callback(**data_next)}])


class SelectWorkedHours(Step):
    """Represent the hours worked selection step in a Telegram bot command."""

    def handle(self, telegram_update):
        """Show the hours worked selection to the user."""
        data = self.get_callback_data(telegram_update)
        options = {"Full day (8h)": 8, "Half day (4h)": 4, "Holiday (0h)": 0}
        keyboard = []
        for key, value in options.items():
            data_duration = dict(data, duration=value)
            keyboard.append([{"text": key, "callback_data": self.next_step_callback(**data_duration)}])

        self.maybe_add_previous_button(keyboard, **data)

        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            f"How many hours did you work on {data['start_date']} for {data['project_name']}:",
            self.command.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )
