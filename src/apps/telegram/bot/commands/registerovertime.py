"""Register overtime command for the Telegram bot."""

import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.projects.models import Project
from apps.telegram.bot.commands.common import Confirm
from apps.telegram.bot.commands.core import Command, Step
from apps.telegram.bot.core import DO_NOTHING, Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.telegram.models import TimeRangeItemTypeRule, WeekdayItemTypeRule
from apps.timesheets.models import Timesheet, TimesheetItem


class RegisterOvertime(Command):
    """Represent the register overtime command."""

    command = "/registerovertime"
    description = "Register overtime for a specific day on a specific project."

    @property
    def steps(self) -> list[Step]:
        """Return the steps of the command."""
        return [
            SelectProject(self),
            SelectDate(self, key="start_date", allow_previous=True),
            WaitForTime(self, key="start_time", date_key="start_date"),
            CombineDateTime(self, date_key="start_date", time_key="start_time"),
            SelectDate(self, key="end_date", unique_id="SelectEndDate"),
            WaitForTime(self, key="end_time", date_key="end_date", unique_id="WaitForEndTime"),
            CombineDateTime(self, date_key="end_date", time_key="end_time", unique_id="CombineEndDateTime"),
            SelectDescription(self),
            SelectItemType(self, allow_previous=True),
            Confirm(self, allow_previous=True),
            InsertTimesheetItems(self),
        ]


class SelectProject(Step):
    """Represent the project selection step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
        """Show the project selection to the user."""
        today = timezone.now().date()
        projects = Project.objects.filter(start_date__lte=today, end_date__gte=today, users=self.command.settings.user)
        if not projects:
            Bot.send_message(
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

        Bot.send_message(
            "Select a project:",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class SelectDate(Step):
    """Represent the date selection step in a Telegram bot command."""

    def __init__(self, command: Command, key: str, allow_previous: bool = False, unique_id: str | None = None):
        """Initialize the date selection step."""
        self.key = key
        super().__init__(command, allow_previous=allow_previous, unique_id=unique_id)

    def handle(self, telegram_update: TelegramUpdate):
        """Display a calendar to pick a date."""
        data = self.get_callback_data(telegram_update)
        now = timezone.now()
        month, year = self._get_month_year(data, now)

        displayed_now = now.replace(month=month, year=year).date()
        previous_month, previous_year = self._get_previous_month_year(displayed_now)
        next_month, next_year = self._get_next_month_year(displayed_now)

        data_previous = {**data, self.key: displayed_now.replace(month=previous_month, year=previous_year)}
        data_next = {**data, self.key: displayed_now.replace(month=next_month, year=next_year)}
        keyboard = []
        header = [
            {"text": "<<", "callback_data": self.current_step_callback(**data_previous)},
            {"text": f"{str(displayed_now.month).zfill(2)}/{displayed_now.year}", "callback_data": DO_NOTHING},
            {"text": ">>", "callback_data": self.current_step_callback(**data_next)},
        ]
        keyboard.append(header)

        days_of_week = [{"text": gettext(day), "callback_data": DO_NOTHING} for day in calendar.day_abbr]
        keyboard.append(days_of_week)

        for week in calendar.monthcalendar(displayed_now.year, displayed_now.month):
            row = []
            for day in week:
                if not day:
                    row.append({"text": " ", "callback_data": DO_NOTHING})
                    continue
                selected_date = date(displayed_now.year, displayed_now.month, day)
                text = str(day).zfill(2)
                if selected_date == now.date():
                    text = f"({text})"
                data_dict = {**data, self.key: selected_date}
                row.append({"text": text, "callback_data": self.next_step_callback(**data_dict)})
            keyboard.append(row)

        self.maybe_add_previous_button(keyboard, **data)

        reply_markup = {"inline_keyboard": keyboard}
        Bot.send_message(
            f"Select the {self.key}:",
            self.command.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )

    def _get_month_year(self, data: dict, now: datetime):
        if data.get(self.key):
            iso_date = date.fromisoformat(data[self.key])
            month = iso_date.month
            year = iso_date.year
        else:
            month = now.month
            year = now.year
        return month, year

    def _get_next_month_year(self, displayed_now: date):
        next_month = displayed_now.month + 1
        next_year = displayed_now.year
        if displayed_now.month == 12:
            next_month = 1
            next_year += 1
        return next_month, next_year

    def _get_previous_month_year(self, displayed_now: date):
        previous_month = displayed_now.month - 1
        previous_year = displayed_now.year
        if displayed_now.month == 1:
            previous_month = 12
            previous_year = displayed_now.year - 1
        return previous_month, previous_year


class WaitForTime(Step):
    """Represent the wait for time input step in a Telegram bot command."""

    def __init__(self, command: Command, key: str, date_key: str, unique_id: str | None = None):
        """Initialize the wait for time input step."""
        self.key = key
        self.date_key = date_key
        super().__init__(command, allow_previous=False, unique_id=unique_id)

    def handle(self, telegram_update: TelegramUpdate):
        """Prompt the user to input a time."""
        data = self.get_callback_data(telegram_update)
        self.add_waiting_for(self.key, data)
        Bot.send_message(
            f"Enter the {self.key} time (HH:MM) for {data[self.date_key]}:",
            self.command.settings.chat_id,
            message_id=telegram_update.message_id,
        )


class CombineDateTime(Step):
    """Represent the combine date and time step in a Telegram bot command."""

    def __init__(self, command: Command, date_key: str, time_key: str, unique_id: str | None = None):
        """Initialize the combine date and time step."""
        self.date_key = date_key
        self.time_key = time_key
        super().__init__(command, allow_previous=False, unique_id=unique_id)

    def handle(self, telegram_update: TelegramUpdate):
        """Combine the date and time into the time_key and move on to the next step."""
        data = self.get_callback_data(telegram_update)
        date_part = date.fromisoformat(data[self.date_key])
        time_part = self._validate_time_format(data[self.time_key])
        combined_datetime = datetime.combine(date_part, time_part)
        data[self.time_key] = combined_datetime.isoformat()
        data.pop(self.date_key)
        telegram_update.callback_data = self.next_step_callback(**data)
        return self.command.next_step(self.name, telegram_update)

    def _validate_time_format(self, time_str: str):
        """Validate and return the time format HH:MM or send an error message.

        - When 1 or 2 digits are provided, they are zfilled and assumed to be the hour.
        - When 3 or 4 digits are provided, they are zfilled and assumed to be HHMM.
        - Otherwise HH:MM is assumed.
        """
        if len(time_str) <= 2:
            normalized_time_str = f"{time_str.zfill(2)}:00"
        elif len(time_str) <= 4:
            time_str_zfilled = time_str.zfill(4)
            normalized_time_str = f"{time_str_zfilled[:2]}:{time_str_zfilled[2:].zfill(2)}"
        else:
            normalized_time_str = time_str

        try:
            return datetime.strptime(normalized_time_str, "%H:%M").time()
        except ValueError as exc:
            Bot.send_message("Invalid time format. Please use HH:MM.", self.command.settings.chat_id)
            raise exc


class SelectDescription(Step):
    """Represent the description selection step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
        """Prompt the user to input a description or select no description."""
        data = self.get_callback_data(telegram_update)
        self.add_waiting_for("description", data)
        data_dict = dict(data, description="")
        keyboard = [[{"text": "No description.", "callback_data": self.next_step_callback(**data_dict)}]]
        Bot.send_message(
            "Send the description (or select 'No description'):",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class SelectItemType(Step):
    """Represent the item type selection step in a Telegram bot command."""

    def handle(self, telegram_update: TelegramUpdate):
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

        Bot.send_message(
            "Select the item type:",
            self.command.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )


class InsertTimesheetItems(Step):
    """Represent the step to insert timesheet items."""

    def handle(self, telegram_update: TelegramUpdate):
        """Insert the timesheet items and go to the next step."""
        data = self.get_callback_data(telegram_update)
        msg = self._try_insert_items(data)
        Bot.send_message(msg, self.command.settings.chat_id, message_id=telegram_update.message_id)
        self.command.next_step(self.name, telegram_update)

    def _try_insert_items(self, data: dict):
        try:
            self._insert_items(data)
        except ValidationError:
            return (
                "The timesheet you are trying to register items for is in an invalid state. Contact your administrator."
            )

        item_type_label = data["item_type_label"]
        start_time = data["start_time"]
        end_time = data["end_time"]
        description = data["description"]
        return f"{item_type_label} registered from {start_time} to {end_time} with description: {description}."

    def _insert_items(self, data: dict):
        """Insert the items into the timesheet.

        Create a timesheet item for each day in the duration between start and end time (inclusive).
        """
        items_to_create = self._prepare_item_batches(data)
        with transaction.atomic():
            timesheets = self._get_or_create_timesheets(items_to_create)
            timesheet_items = self._assign_timesheet_to_items(items_to_create, timesheets)
            TimesheetItem.objects.bulk_create(timesheet_items)

    def _assign_timesheet_to_items(
        self, items_to_create: defaultdict[tuple, list[TimesheetItem]], timesheets: dict[tuple, Timesheet]
    ):
        timesheet_items = []
        for key, items in items_to_create.items():
            timesheet = timesheets[key]
            for item in items:
                item.timesheet = timesheet
            timesheet_items.extend(items)
        return timesheet_items

    def _get_or_create_timesheets(self, items_to_create: defaultdict[tuple, list]):
        timesheets: dict[tuple[int, int, int], Timesheet] = {}
        for timesheet_key in items_to_create.keys():
            month, year, project_id = timesheet_key
            timesheet, _created = Timesheet.objects.get_or_create(
                user=self.command.settings.user,
                month=month,
                year=year,
                project_id=project_id,
                status=Timesheet.Status.DRAFT,
            )
            timesheets[timesheet_key] = timesheet
        return timesheets

    def _prepare_item_batches(self, data: dict):
        start_time = datetime.fromisoformat(data["start_time"])
        end_time = datetime.fromisoformat(data["end_time"])
        current_date = start_time.date()
        end_date = end_time.date()

        items_to_create: defaultdict[tuple[int, int, int], list[TimesheetItem]] = defaultdict(list)
        while current_date <= end_date:
            day_start_time = self._get_day_start_time(current_date, start_time)
            day_end_time = self._get_day_end_time(current_date, end_time)
            if self._add_non_inferred_item(data, items_to_create, day_start_time, day_end_time, current_date):
                current_date += timedelta(days=1)
                continue

            if self._add_weekday_item(data, items_to_create, day_start_time, day_end_time, current_date):
                current_date += timedelta(days=1)
                continue

            self._add_timerange_items(data, items_to_create, day_start_time, day_end_time, current_date)
            current_date += timedelta(days=1)
        return items_to_create

    def _get_day_end_time(self, current_date: date, end_time: datetime):
        next_day_midnight = datetime.combine(current_date + timedelta(days=1), datetime.min.time())
        return min(end_time, next_day_midnight)

    def _get_day_start_time(self, current_date: date, start_time: datetime):
        day_start_time = datetime.combine(current_date, datetime.min.time())
        return max(day_start_time, start_time)

    def _add_non_inferred_item(
        self,
        data: dict,
        items_to_create: defaultdict[tuple, list],
        day_start_time: datetime,
        day_end_time: datetime,
        current_date: date,
    ):
        item_type = data["item_type"]
        if not item_type:
            return False
        self._add_item(data, items_to_create, day_start_time, day_end_time, current_date, item_type)
        return True

    def _add_weekday_item(
        self,
        data: dict,
        items_to_create: defaultdict[tuple, list],
        day_start_time: datetime,
        day_end_time: datetime,
        current_date: date,
    ):
        weekday = day_start_time.weekday()
        matching_rule = WeekdayItemTypeRule.objects.filter(weekday=weekday).first()
        if not matching_rule:
            return False
        self._add_item(data, items_to_create, day_start_time, day_end_time, current_date, matching_rule.item_type)
        return True

    def _add_timerange_items(
        self,
        data: dict,
        items_to_create: defaultdict[tuple, list],
        day_start_time: datetime,
        day_end_time: datetime,
        current_date: date,
    ):
        rules = TimeRangeItemTypeRule.objects.all()
        for rule in rules:
            rule_start = datetime.combine(current_date, rule.start_time)
            rule_end = datetime.combine(current_date, rule.end_time)
            if rule_end <= rule_start:
                # Evening segment (current day)
                seg_start = max(day_start_time, rule_start)
                seg_end = min(day_end_time, datetime.combine(current_date + timedelta(days=1), datetime.min.time()))
                if seg_start < seg_end:
                    self._add_item(data, items_to_create, seg_start, seg_end, current_date, rule.item_type)
                # Morning segment (current day)
                morning_start = datetime.combine(current_date, datetime.min.time())
                morning_end = datetime.combine(current_date, rule.end_time)
                seg_start = max(day_start_time, morning_start)
                seg_end = min(day_end_time, morning_end)
                if seg_start < seg_end:
                    self._add_item(data, items_to_create, seg_start, seg_end, current_date, rule.item_type)
            else:
                seg_start = max(day_start_time, rule_start)
                seg_end = min(day_end_time, rule_end)
                if seg_start < seg_end:
                    self._add_item(data, items_to_create, seg_start, seg_end, current_date, rule.item_type)

    def _add_item(
        self,
        data: dict,
        items_to_create: defaultdict[tuple, list],
        start_time: datetime,
        end_time: datetime,
        current_date: date,
        item_type: int,
    ):
        worked_hours = (end_time - start_time).total_seconds() / 3600
        timesheet_key = (current_date.month, current_date.year, int(data["project_id"]))
        items_to_create[timesheet_key].append(
            TimesheetItem(
                date=current_date,
                worked_hours=worked_hours,
                description=data["description"],
                item_type=item_type,
            )
        )
