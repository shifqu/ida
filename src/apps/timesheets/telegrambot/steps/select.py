"""Steps that handle selection of items in the Telegram bot.

This is usually done by showing inline keyboards with options to choose from.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.translation import gettext

from apps.projects.models import Project
from apps.telegram.bot.base import Step
from apps.telegram.bot.bot import DO_NOTHING, send_message
from apps.timesheets.models import Timesheet, TimesheetItem
from apps.timesheets.telegrambot.steps._types import OverviewType

if TYPE_CHECKING:
    from apps.telegram.bot.base import BaseCommand, TelegramUpdate


class SelectDate(Step):
    """Represent the date selection step in a Telegram bot command."""

    def __init__(
        self,
        command: BaseCommand,
        key: str,
        initial_date_key: str = "",
        steps_back: int = 0,
        unique_id: str | None = None,
    ):
        """Initialize the date selection step."""
        self.key = key
        self.initial_date_key = initial_date_key
        super().__init__(command, steps_back=steps_back, unique_id=unique_id)

    def handle(self, telegram_update: "TelegramUpdate"):
        """Display a calendar to pick a date."""
        data = self.get_callback_data(telegram_update)
        now = timezone.now()
        display_date = self._get_display_date(data, now)

        data_previous = {**data, self.key: self._get_previous_display_date(display_date)}
        data_next = {**data, self.key: self._get_next_display_date(display_date)}
        keyboard = []
        header = [
            {"text": "<<", "callback_data": self.current_step_callback(**data_previous)},
            {"text": f"{str(display_date.month).zfill(2)}/{display_date.year}", "callback_data": DO_NOTHING},
            {"text": ">>", "callback_data": self.current_step_callback(**data_next)},
        ]
        keyboard.append(header)

        days_of_week = [{"text": gettext(day), "callback_data": DO_NOTHING} for day in calendar.day_abbr]
        keyboard.append(days_of_week)

        for week in calendar.monthcalendar(display_date.year, display_date.month):
            row = []
            for day in week:
                if not day:
                    row.append({"text": " ", "callback_data": DO_NOTHING})
                    continue
                selected_date = date(display_date.year, display_date.month, day)
                text = str(day).zfill(2)
                if selected_date == now.date():
                    text = f"({text})"
                data_dict = {**data, self.key: selected_date}
                row.append({"text": text, "callback_data": self.next_step_callback(**data_dict)})
            keyboard.append(row)

        self.maybe_add_previous_button(keyboard, **data)

        reply_markup = {"inline_keyboard": keyboard}
        send_message(
            f"Select the {self.key}:",
            self.command.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )

    def _get_display_date(self, data: dict, now: datetime):
        if data.get(self.key):
            iso_date = datetime.fromisoformat(data[self.key])
            month = iso_date.month
            year = iso_date.year
        elif self.initial_date_key and data.get(self.initial_date_key):
            iso_date = datetime.fromisoformat(data[self.initial_date_key]).date()
            month = iso_date.month
            year = iso_date.year
        else:
            month = now.month
            year = now.year
        return date(year, month, 1)

    def _get_next_display_date(self, displayed_date: date):
        next_month = displayed_date.month + 1
        next_year = displayed_date.year
        if displayed_date.month == 12:
            next_month = 1
            next_year += 1
        return displayed_date.replace(year=next_year, month=next_month)

    def _get_previous_display_date(self, displayed_date: date):
        previous_month = displayed_date.month - 1
        previous_year = displayed_date.year
        if displayed_date.month == 1:
            previous_month = 12
            previous_year = displayed_date.year - 1
        return displayed_date.replace(year=previous_year, month=previous_month)


class SelectDay(Step):
    """Represent the day selection step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the day selection to the user."""
        days = self.get_days()
        if not days:
            msg = f"No days found. Unable to complete {self.command.get_name()}."
            send_message(msg, telegram_update.chat_id)
            return self.command.finish(self.name, telegram_update)

        data = self.get_callback_data(telegram_update)
        current_page: int = data.get("current_page", 1)
        start = (current_page - 1) * 4
        end = start + 4

        keyboard = self.get_keyboard(days, data, start, end)

        self._maybe_add_pagination_buttons(keyboard, days, data, current_page, end)

        self.maybe_add_previous_button(keyboard, **data)

        reply_markup = {"inline_keyboard": keyboard}
        send_message(
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


class SelectItemType(Step):
    """Represent the item type selection step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the item type selection to the user."""
        data = self.get_callback_data(telegram_update)
        keyboard = []
        for item_type in TimesheetItem.ItemType:
            data_item = dict(data, item_type=item_type.value, item_type_label=item_type.label)
            keyboard.append(
                [
                    {
                        "text": str(item_type.label),  # Needs str cast for lazy translation objects
                        "callback_data": self.next_step_callback(**data_item),
                    }
                ]
            )

        # Add the infer item type
        data_infer = dict(data, item_type=0, item_type_label="Inferred")
        keyboard.append(
            [
                {
                    "text": "Inferred",
                    "callback_data": self.next_step_callback(**data_infer),
                }
            ]
        )

        self.maybe_add_previous_button(keyboard, **data)

        send_message(
            "Select the item type:",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


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


class SelectOverviewType(Step):
    """Represent the overview type selection step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
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

        send_message(
            "Which type of overview would you like to see?",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class SelectProject(Step):
    """Represent the project selection step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the project selection to the user."""
        today = timezone.now().date()
        projects = Project.objects.filter(start_date__lte=today, end_date__gte=today, users=self.command.settings.user)
        if not projects:
            send_message(
                "No active projects found. Please contact your administrator.",
                self.command.settings.chat_id,
                message_id=telegram_update.message_id,
            )
            return self.command.finish(self.name, telegram_update)

        data = self.get_callback_data(telegram_update)
        if len(projects) == 1:
            data["project_id"] = projects[0].pk
            data["project_name"] = str(projects[0])
            telegram_update.callback_data = self.next_step_callback(**data)
            return self.command.next_step(self.name, telegram_update)

        keyboard = []
        for project in projects:
            data["project_id"] = project.pk
            data["project_name"] = str(project)
            keyboard.append([{"text": str(project), "callback_data": self.next_step_callback(**data)}])

        self.maybe_add_previous_button(keyboard, **data)

        send_message(
            "Select a project:",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class SelectTimesheet(Step):
    """Represent the timesheet selection step in a Telegram bot command."""

    def __init__(
        self,
        command: BaseCommand,
        steps_back: int = 0,
        filter_kwargs: dict | None = None,
        order_by: tuple | None = None,
        unique_id: str | None = None,
    ):
        """Initialize the timesheet selection step."""
        self.filter_kwargs = filter_kwargs or dict(user=command.settings.user, status=Timesheet.Status.DRAFT)
        self.order_by = order_by or ("-year", "-month")
        super().__init__(command, steps_back=steps_back, unique_id=unique_id)

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the timesheet selection to the user."""
        logging.info(f"Handling {self.name} step for user {self.command.settings.user}")
        timesheets = Timesheet.objects.filter(**self.filter_kwargs).order_by(*self.order_by)
        if not timesheets:
            error_message = "No timesheets found."
            send_message(error_message, self.command.settings.chat_id, message_id=telegram_update.message_id)
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

        send_message(
            "Select a timesheet:",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


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
        send_message(
            f"How many hours did you work on {data['start_date']} for {data['project_name']}:",
            self.command.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )
