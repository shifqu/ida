"""Register overtime command for the Telegram bot."""

import calendar
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.projects.models import Project
from apps.telegram.bot.commands.base import CommandDataWithConfirm, CommandWithConfirm
from apps.telegram.bot.core import DO_NOTHING, Bot
from apps.telegram.bot.types import TelegramUpdate
from apps.telegram.models import TimeRangeItemTypeRule, WeekdayItemTypeRule
from apps.timesheets.models import Timesheet, TimesheetItem


@dataclass
class OvertimeData(CommandDataWithConfirm):
    """Represent the data for the register overtime command."""

    project_id: int | None = None
    project_name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    description: str | None = None
    item_type: str | None = None

    @classmethod
    def fromdict(cls, data: dict):
        """Create an instance from a dictionary."""
        instance = super().fromdict(data)
        if instance.start_time and isinstance(instance.start_time, str):
            instance.start_time = datetime.fromisoformat(instance.start_time)
        if instance.end_time and isinstance(instance.end_time, str):
            instance.end_time = datetime.fromisoformat(instance.end_time)
        return instance

    def get_item_type_label(self):
        """Get the item type label."""
        if self.item_type == "infer":
            return "Inferred"
        return TimesheetItem.ItemType(self.item_type).label


class RegisterOvertime(CommandWithConfirm[OvertimeData]):
    """Represent the register overtime command."""

    name = "/registerovertime"
    data_class = OvertimeData

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the command."""
        self._show_project_selection(telegram_update)

    def _show_project_selection(self, telegram_update: TelegramUpdate):
        """Show the project selection for the command.

        If only one project is available, it will be selected automatically and this step is skipped.
        """
        today = timezone.now().date()
        projects = Project.objects.filter(start_date__lte=today, end_date__gte=today, users=self.settings.user)
        if not projects:
            Bot.send_message(
                "You have no active projects assigned. Please contact your administrator.",
                self.settings.chat_id,
                message_id=telegram_update.message_id,
            )
            return

        data = self.data_class()
        if len(projects) == 1:
            data.project_id = projects[0].pk
            data.project_name = str(projects[0])
            telegram_update.callback_data = self.create_callback("_show_date_selection", **data.asdict())
            self._show_date_selection(telegram_update)
            return

        keyboard = []
        for project in projects:
            data.project_id = project.pk
            data.project_name = str(project)
            keyboard.append(
                [
                    {
                        "text": str(project),
                        "callback_data": self.create_callback("_show_date_selection", **data.asdict()),
                    }
                ]
            )

        Bot.send_message(
            "Please select a project:",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _show_date_selection(self, telegram_update: TelegramUpdate):
        """Display a calendar to pick a date."""
        data = self.get_command_data(telegram_update.callback_data)
        now = timezone.now()
        month, year, key = self._get_key_month_year(data, now)

        displayed_now = now.replace(month=month, year=year)
        previous_month, previous_year = self._get_previous_month_year(displayed_now)
        next_month, next_year = self._get_next_month_year(displayed_now)

        data_dict = data.asdict()
        data_previous = {**data_dict, key: displayed_now.replace(month=previous_month, year=previous_year)}
        data_next = {**data_dict, key: displayed_now.replace(month=next_month, year=next_year)}
        keyboard = []
        header = [
            {"text": "<<", "callback_data": self.create_callback("_show_date_selection", **data_previous)},
            {"text": f"{str(displayed_now.month).zfill(2)}/{displayed_now.year}", "callback_data": DO_NOTHING},
            {"text": ">>", "callback_data": self.create_callback("_show_date_selection", **data_next)},
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
                data_dict = {**data_dict, key: datetime.combine(selected_date, datetime.min.time())}
                row.append(
                    {
                        "text": text,
                        "callback_data": self.create_callback("_handle_date_selection", **data_dict),
                    }
                )
            keyboard.append(row)
        reply_markup = {"inline_keyboard": keyboard}

        Bot.send_message(
            "Please select a day:",
            self.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )

    def _get_key_month_year(self, data: OvertimeData, now: datetime):
        if data.end_time:
            month = data.end_time.month
            year = data.end_time.year
            key = "end_time"
        elif data.start_time:
            month = data.start_time.month
            year = data.start_time.year
            key = "start_time"
        else:
            month = now.month
            year = now.year
            key = "start_time"
        return month, year, key

    def _handle_date_selection(self, telegram_update: TelegramUpdate):
        step_data = self.get_command_data(telegram_update.callback_data)
        if step_data.end_time:
            key = "end"
            date_to_display = step_data.end_time.date()
        elif step_data.start_time:
            key = "start"
            date_to_display = step_data.start_time.date()
        else:
            Bot.send_message(
                "No start or end time set in step data.", self.settings.chat_id, message_id=telegram_update.message_id
            )
            raise ValueError("No start or end time set in step data.")
        self.settings.data["waiting_for"] = self.create_callback("_handle_time_input", **step_data.asdict())
        self.settings.save()
        Bot.send_message(
            f"Ok. What's the {key} time on {date_to_display}?",
            self.settings.chat_id,
            message_id=telegram_update.message_id,
        )

    def _handle_time_input(self, telegram_update: TelegramUpdate):
        time_str = telegram_update.message_text.strip()
        time = self._validate_time_format(time_str)

        step_data = self.get_command_data(self.settings.data["waiting_for"])
        if step_data.end_time:
            step_data.end_time = datetime.combine(step_data.end_time.date(), time)
            telegram_update.callback_data = self.create_callback("_show_description_input", **step_data.asdict())
            return self._show_description_input(telegram_update)

        if step_data.start_time:
            step_data.start_time = datetime.combine(step_data.start_time.date(), time)
            step_data.end_time = step_data.start_time

            telegram_update.callback_data = self.create_callback("_show_date_selection", **step_data.asdict())
            return self._show_date_selection(telegram_update)

        Bot.send_message(
            "No start or end time set in step data.", self.settings.chat_id, message_id=telegram_update.message_id
        )
        raise ValueError("No start or end time set in step data.")

    def _show_description_input(self, telegram_update: TelegramUpdate):
        callback = self.get_callback(telegram_update.callback_data)
        callback_str = self.create_callback("_handle_description_input", **callback.data)
        self.settings.data["waiting_for"] = callback_str
        self.settings.save()

        keyboard = [[{"text": "No description.", "callback_data": callback_str}]]
        Bot.send_message(
            "Ok. Please send me the description.",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_description_input(self, telegram_update: TelegramUpdate):
        description = telegram_update.message_text.strip()
        step_data = self.get_command_data(self.settings.data["waiting_for"])
        step_data.description = description

        keyboard = []
        for item_type in TimesheetItem.ItemType:
            step_data.item_type = item_type.value
            row = [
                {
                    "text": str(item_type.label),
                    "callback_data": self.create_callback("_handle_item_type_selection", **step_data.asdict()),
                }
            ]
            keyboard.append(row)

        # Add the infer item type
        step_data_infer = replace(step_data, item_type="infer")
        keyboard.append(
            [
                {
                    "text": step_data_infer.get_item_type_label(),
                    "callback_data": self.create_callback("_handle_item_type_selection", **step_data_infer.asdict()),
                }
            ]
        )

        Bot.send_message(
            "Select the item type:",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_item_type_selection(self, telegram_update: TelegramUpdate):
        step_data = self.get_command_data(telegram_update.callback_data)
        item_type_label = step_data.get_item_type_label()
        msg = (
            "Would you like to register time for the following details:\n"
            f"Project Name: {step_data.project_name}\n"
            f"Start: {step_data.start_time}\n"
            f"End: {step_data.end_time}\n"
            f"Description: {step_data.description}\n"
            f"Item Type: {item_type_label}"
        )
        self._show_confirmation(step_data, msg, telegram_update)

    def _finish_command(self, telegram_update: TelegramUpdate):
        step_data = self.get_command_data(telegram_update.callback_data)
        if step_data.confirmation:
            msg = self._try_insert_items(step_data)
        else:
            msg = "Command canceled."

        Bot.send_message(msg, self.settings.chat_id, message_id=telegram_update.message_id)
        return step_data.correlation_key

    def _try_insert_items(self, step_data: OvertimeData):
        try:
            self._insert_items(step_data)
        except ValidationError:
            return (
                "The timesheet you are trying to register items for is in an invalid state. Contact your administrator."
            )

        item_type_label = step_data.get_item_type_label()
        return f"{item_type_label} registered from {step_data.start_time} to {step_data.end_time} with description: {step_data.description}."

    def _insert_items(self, step_data: OvertimeData):
        """Insert the items into the timesheet.

        Create a timesheet item for each day in the duration between start and end time (inclusive).
        """
        items_to_create = self._prepare_item_batches(step_data)
        with transaction.atomic():
            timesheets: dict[tuple[int, int, int], Timesheet] = {}
            for timesheet_key in items_to_create.keys():
                month, year, project_id = timesheet_key
                timesheet, _created = Timesheet.objects.get_or_create(
                    user=self.settings.user,
                    month=month,
                    year=year,
                    project_id=project_id,
                    status=Timesheet.Status.DRAFT,
                )
                timesheets[timesheet_key] = timesheet

            timesheet_items = []
            for key, items in items_to_create.items():
                timesheet = timesheets[key]
                for item in items:
                    item.timesheet = timesheet
                timesheet_items.extend(items)

            TimesheetItem.objects.bulk_create(timesheet_items)

    def _prepare_item_batches(self, step_data: OvertimeData):
        assert step_data.start_time and step_data.end_time and step_data.project_id, (
            "Start time, end time and project_id must be set to insert items."
        )
        current_date = step_data.start_time.date()
        end_date = step_data.end_time.date()

        items_to_create: defaultdict[tuple[int, int, int], list[TimesheetItem]] = defaultdict(list)
        while current_date <= end_date:
            day_start_time = self._get_day_start_time(current_date, step_data.start_time)
            day_end_time = self._get_day_end_time(current_date, step_data.end_time)
            if self._add_non_inferred_item(step_data, items_to_create, day_start_time, day_end_time, current_date):
                current_date = self._get_next_day(current_date)
                continue

            if self._add_weekday_item(step_data, items_to_create, day_start_time, day_end_time, current_date):
                current_date = self._get_next_day(current_date)
                continue

            self._add_timerange_items(step_data, items_to_create, day_start_time, day_end_time, current_date)
            current_date = self._get_next_day(current_date)
        return items_to_create

    def _get_day_end_time(self, current_date: date, end_time: datetime):
        next_day_midnight = datetime.combine(current_date + timedelta(days=1), datetime.min.time())
        return min(end_time, next_day_midnight)

    def _get_day_start_time(self, current_date: date, start_time: datetime):
        day_start_time = datetime.combine(current_date, datetime.min.time())
        return max(day_start_time, start_time)

    def _get_next_day(self, current_date: date):
        return current_date + timedelta(days=1)

    def _add_non_inferred_item(
        self,
        step_data: OvertimeData,
        items_to_create: defaultdict[tuple, list],
        day_start_time: datetime,
        day_end_time: datetime,
        current_date: date,
    ):
        if not step_data.item_type or step_data.item_type == "infer":
            return False
        worked_hours = (day_end_time - day_start_time).total_seconds() / 3600
        timesheet_key = (day_start_time.month, day_start_time.year, step_data.project_id)
        items_to_create[timesheet_key].append(
            TimesheetItem(
                date=current_date,
                worked_hours=worked_hours,
                description=step_data.description,
                item_type=step_data.item_type,
            )
        )
        return True

    def _add_weekday_item(
        self,
        step_data: OvertimeData,
        items_to_create: defaultdict[tuple, list],
        day_start_time: datetime,
        day_end_time: datetime,
        current_date: date,
    ):
        weekday = day_start_time.weekday()
        matching_rule = WeekdayItemTypeRule.objects.filter(weekday=weekday).first()
        if not matching_rule:
            return False
        worked_hours = (day_end_time - day_start_time).total_seconds() / 3600
        timesheet_key = (day_start_time.month, day_start_time.year, step_data.project_id)
        items_to_create[timesheet_key].append(
            TimesheetItem(
                date=current_date,
                worked_hours=worked_hours,
                description=step_data.description,
                item_type=matching_rule.item_type,
            )
        )
        return True

    def _add_timerange_items(
        self,
        step_data: OvertimeData,
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
                    worked_hours = (seg_end - seg_start).total_seconds() / 3600
                    items_to_create[(current_date.month, current_date.year, step_data.project_id)].append(
                        TimesheetItem(
                            date=current_date,
                            worked_hours=worked_hours,
                            description=step_data.description,
                            item_type=rule.item_type,
                        )
                    )
                # Morning segment (current day)
                morning_start = datetime.combine(current_date, datetime.min.time())
                morning_end = datetime.combine(current_date, rule.end_time)
                seg_start = max(day_start_time, morning_start)
                seg_end = min(day_end_time, morning_end)
                if seg_start < seg_end:
                    worked_hours = (seg_end - seg_start).total_seconds() / 3600
                    items_to_create[(current_date.month, current_date.year, step_data.project_id)].append(
                        TimesheetItem(
                            date=current_date,
                            worked_hours=worked_hours,
                            description=step_data.description,
                            item_type=rule.item_type,
                        )
                    )
            else:
                seg_start = max(day_start_time, rule_start)
                seg_end = min(day_end_time, rule_end)
                if seg_start < seg_end:
                    worked_hours = (seg_end - seg_start).total_seconds() / 3600
                    items_to_create[(current_date.month, current_date.year, step_data.project_id)].append(
                        TimesheetItem(
                            date=current_date,
                            worked_hours=worked_hours,
                            description=step_data.description,
                            item_type=rule.item_type,
                        )
                    )

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
            Bot.send_message("Invalid time format. Please use HH:MM.", self.settings.chat_id)
            raise exc

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
