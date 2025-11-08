"""Steps that handle actions in the Telegram bot."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.telegram.bot.base import Step
from apps.telegram.bot.bot import send_message
from apps.timesheets.models import TimeRangeItemTypeRule, Timesheet, TimesheetItem, WeekdayItemTypeRule

if TYPE_CHECKING:
    from apps.telegram.bot.base import BaseCommand, TelegramUpdate


class CombineDateTime(Step):
    """Represent the combine date and time step in a Telegram bot command."""

    def __init__(self, command: BaseCommand, date_key: str, time_key: str, unique_id: str | None = None):
        """Initialize the combine date and time step."""
        self.date_key = date_key
        self.time_key = time_key
        super().__init__(command, steps_back=0, unique_id=unique_id)

    def handle(self, telegram_update: "TelegramUpdate"):
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
            send_message("Invalid time format. Please use HH:MM.", self.command.settings.chat_id)
            raise exc


class EditWorkedHours(Step):
    """Represent the editing of work step in a Telegram bot command."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Confirm if the editing of work was successful or not."""
        data = self.get_callback_data(telegram_update)
        msg = self._try_editwork(data)
        send_message(msg, self.command.settings.chat_id, message_id=telegram_update.message_id)
        return self.command.next_step(self.name, telegram_update)

    def _try_editwork(self, data: dict):
        try:
            self._editwork(data)
        except Timesheet.DoesNotExist:
            # Could happen when a user is filling in working hours, but in the meantime the timesheet was completed.
            msg = "The timesheet you are trying to edit work for is in an invalid state. Contact your administrator."
        else:
            msg = f"Successfully edited {data['duration']}h for {data['project_name']} on {data['start_date']}."
        return msg

    def _editwork(self, data: dict):
        """Edit working hours for the given date and option."""
        timesheet_item = TimesheetItem.objects.get(pk=data["item_pk"], timesheet__status=Timesheet.Status.DRAFT)
        timesheet_item.worked_hours = data["duration"]
        timesheet_item.save()


class InsertTimesheetItems(Step):
    """Represent the step to insert timesheet items."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Insert the timesheet items and go to the next step."""
        data = self.get_callback_data(telegram_update)
        msg = self._try_insert_items(data)
        send_message(msg, self.command.settings.chat_id, message_id=telegram_update.message_id)
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


class MarkTimesheetAsCompleted(Step):
    """Represent the step to mark the selected timesheet as completed."""

    def handle(self, telegram_update: "TelegramUpdate"):
        """Show the mark timesheet as completed step."""
        data = self.get_callback_data(telegram_update)
        timesheet = Timesheet.objects.get(pk=data["timesheet_id"])
        timesheet.mark_as_completed()

        send_message(
            f"Successfully marked the timesheet {timesheet} as completed.",
            self.command.settings.chat_id,
            message_id=telegram_update.message_id,
        )
        self.command.next_step(self.name, telegram_update)


class RegisterWorkedHours(Step):
    """Represent the registration of work step in a Telegram bot command."""

    def handle(self, telegram_update):
        """Confirm if the registraiton of work was successful or not."""
        data = self.get_callback_data(telegram_update)
        msg = self._try_registerwork(data)
        send_message(msg, self.command.settings.chat_id, message_id=telegram_update.message_id)

    def _try_registerwork(self, data: dict):
        try:
            self._registerwork(data)
        except Timesheet.DoesNotExist:
            # Could happen when a user is filling in working hours, but in the meantime the timesheet was completed.
            msg = (
                "The timesheet you are trying to register work for is in an invalid state. Contact your administrator."
            )
        else:
            msg = f"Successfully registered {data['duration']}h for {data['project_name']} on {data['start_date']}."
        return msg

    def _registerwork(self, data: dict):
        """Register work hours for the given date and option."""
        assert data["start_date"], "Start date must be set."
        start_date = date.fromisoformat(data["start_date"])
        timesheet = Timesheet.objects.get(
            status=Timesheet.Status.DRAFT,
            month=start_date.month,
            year=start_date.year,
            user=self.command.settings.user,
            project_id=data["project_id"],
        )
        timesheet.timesheetitem_set.create(date=start_date, worked_hours=data["duration"])
