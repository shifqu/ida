"""Register overtime command for the Telegram bot."""

import calendar
from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext

from apps.projects.models import Project
from apps.telegram.bot.commands.base import Command
from apps.telegram.bot.core import DO_NOTHING, Bot
from apps.telegram.types import TelegramUpdate
from apps.timesheets.models import Timesheet, TimesheetItem


class RegisterOvertime(Command):
    """Represent the register overtime command."""

    name = "/registerovertime"

    def _start_command(self, telegram_update: TelegramUpdate):
        """Start the register overtime command."""
        self._show_project_selection(telegram_update)

    def _show_project_selection(self, telegram_update: TelegramUpdate):
        """Show the project selection for the overtime.

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

        if len(projects) == 1:
            telegram_update.callback_data = f"{self.name}|_handle_project_selection|{projects[0].pk}"
            self._handle_project_selection(telegram_update)
            return

        keyboard = [
            [{"text": str(project), "callback_data": f"{self.name}|_handle_project_selection|{project.pk}"}]
            for project in projects
        ]
        Bot.send_message(
            "Please select a project:",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_project_selection(self, telegram_update: TelegramUpdate):
        _command, _step, project_id_str = telegram_update.callback_data.split("|")
        project_id = int(project_id_str)
        self.settings.data["project_id"] = project_id
        self.settings.save()

        telegram_update.callback_data = ""
        self._show_date_selection(telegram_update)

    def _show_date_selection(self, telegram_update: TelegramUpdate):
        """Display a calendar to pick a date."""
        now = timezone.now()
        displayed_now = now.date()
        if telegram_update.callback_data:
            _command, _step, month, year = telegram_update.callback_data.split("|")
            month = int(month)
            year = int(year)
            displayed_now = displayed_now.replace(month=month, year=year)

        previous_month, previous_year = self._get_previous_month_year(displayed_now)
        next_month, next_year = self._get_next_month_year(displayed_now)

        keyboard = []
        header = [
            {"text": "<<", "callback_data": f"{self.name}|_show_date_selection|{previous_month}|{previous_year}"},
            {"text": f"{str(displayed_now.month).zfill(2)}/{displayed_now.year}", "callback_data": DO_NOTHING},
            {"text": ">>", "callback_data": f"{self.name}|_show_date_selection|{next_month}|{next_year}"},
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
                    text = f"({day})"
                row.append({"text": text, "callback_data": f"{self.name}|_handle_date_selection|{selected_date}"})
            keyboard.append(row)
        reply_markup = {"inline_keyboard": keyboard}

        Bot.send_message(
            "Please select a day:",
            self.settings.chat_id,
            reply_markup=reply_markup,
            message_id=telegram_update.message_id,
        )
        return True

    def _handle_date_selection(self, telegram_update: TelegramUpdate):
        _command, _step, selected_date_str = telegram_update.callback_data.split("|")
        self.settings.data["waiting_for"] = f"{self.name}|_handle_start_time_input"
        self.settings.data["selected_date"] = selected_date_str
        self.settings.save()

        Bot.send_message(
            "Ok. Please send me the start ([H]H/[H]HMM/[H]H:[M]M).",
            self.settings.chat_id,
            message_id=telegram_update.message_id,
        )

    def _handle_start_time_input(self, telegram_update: TelegramUpdate):
        start_time_str = telegram_update.message_text.strip()
        start_time = self._validate_time_format(start_time_str)

        self.settings.data["waiting_for"] = f"{self.name}|_handle_duration_input"
        self.settings.data["start_time"] = f"{start_time.hour:02}:{start_time.minute:02}"
        self.settings.save()

        Bot.send_message(
            "Ok. Please send me the duration ([H]H/[H]HMM/[H]H:[M]M).",
            self.settings.chat_id,
            message_id=telegram_update.message_id,
        )

    def _handle_duration_input(self, telegram_update: TelegramUpdate):
        duration_str = telegram_update.message_text.strip()
        duration = self._validate_time_format(duration_str)

        self.settings.data["waiting_for"] = f"{self.name}|_handle_description_input"
        self.settings.data["duration"] = f"{duration.hour:02}:{duration.minute:02}"
        self.settings.save()

        self._show_description_input(telegram_update)

    def _show_description_input(self, telegram_update):
        keyboard = [[{"text": "No description.", "callback_data": f"{self.name}|_handle_description_input"}]]
        Bot.send_message(
            "Ok. Please send me the description.",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_description_input(self, telegram_update: TelegramUpdate):
        description = telegram_update.message_text.strip()
        self.settings.data["description"] = description
        self.settings.save()

        self._show_item_type_selection(telegram_update)

    def _show_item_type_selection(self, telegram_update: TelegramUpdate):
        keyboard = [
            [
                {
                    "text": str(item_type.label),
                    "callback_data": f"{self.name}|_handle_item_type_selection|{item_type.value}",
                }
            ]
            for item_type in TimesheetItem.ItemType
        ]
        Bot.send_message(
            "Select the item type for the overtime:",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_item_type_selection(self, telegram_update: TelegramUpdate):
        _command, _step, item_type = telegram_update.callback_data.split("|")
        self.settings.data["item_type"] = item_type
        self.settings.save()

        self._show_confirmation_selection(telegram_update)

    def _show_confirmation_selection(self, telegram_update: TelegramUpdate):
        project_id = int(self.settings.data["project_id"])
        selected_date = self.settings.data["selected_date"]
        start_time_str = self.settings.data["start_time"]
        duration_str = self.settings.data["duration"]
        description = self.settings.data["description"]
        item_type = self.settings.data["item_type"]

        duration = self._validate_time_format(duration_str)
        start = datetime.fromisoformat(f"{selected_date}T{start_time_str}")
        end = start + timedelta(hours=duration.hour, minutes=duration.minute)

        keyboard = [
            [{"text": gettext("yes"), "callback_data": f"{self.name}|_handle_confirmation_selection|1"}],
            [{"text": gettext("no"), "callback_data": f"{self.name}|_handle_confirmation_selection|0"}],
        ]
        Bot.send_message(
            "Would you like to register overtime for the following details:\n"
            f"Project ID: {project_id}\n"
            f"Start: {start}\n"
            f"End: {end}\n"
            f"Description: {description}\n"
            f"Item Type: {item_type}",
            self.settings.chat_id,
            reply_markup={"inline_keyboard": keyboard},
            message_id=telegram_update.message_id,
        )

    def _handle_confirmation_selection(self, telegram_update: TelegramUpdate):
        _command, _step, confirmation_str = telegram_update.callback_data.split("|")
        confirmed = int(confirmation_str)
        if confirmed:
            self._finalize_command(telegram_update)
        else:
            self.clear_state()
            Bot.send_message(
                "Overtime registration canceled.", self.settings.chat_id, message_id=telegram_update.message_id
            )

    def _finalize_command(self, telegram_update: TelegramUpdate):
        project_id = int(self.settings.data["project_id"])
        selected_date = self.settings.data["selected_date"]
        start_time_str = self.settings.data["start_time"]
        duration_str = self.settings.data["duration"]
        description = self.settings.data["description"]
        item_type = self.settings.data["item_type"]

        start = datetime.fromisoformat(f"{selected_date}T{start_time_str}")
        duration = self._validate_time_format(duration_str)
        end = start + timedelta(hours=duration.hour, minutes=duration.minute)

        try:
            self._insert_items(project_id, description, item_type, start, end)
        except ValidationError:
            msg = (
                "The timesheet you are trying to register overtime for is in an invalid state. "
                "Contact your administrator."
            )
        else:
            msg = f"Overtime registered from {start} to {end} with description: {description}."

        self.clear_state()
        Bot.send_message(msg, self.settings.chat_id, message_id=telegram_update.message_id)

    def _insert_items(self, project_id: int, description: str, item_type: str, start: datetime, end: datetime):
        """Insert the items into the timesheet.

        If the end date is on the next day, create two timesheet items, otherwise create one.
        """
        if end.date() > start.date():
            end_beginning_of_day = end.replace(hour=0, minute=0, second=0, microsecond=0)
            worked_hours_day_1 = (end_beginning_of_day - start).total_seconds() / 3600
            worked_hours_day_2 = (end - end_beginning_of_day).total_seconds() / 3600
            with transaction.atomic():
                self._insert_item(project_id, description, item_type, start, worked_hours_day_1)
                self._insert_item(project_id, description, item_type, end, worked_hours_day_2)
        else:
            worked_hours_day_1 = (end - start).total_seconds() / 3600
            self._insert_item(project_id, description, item_type, start, worked_hours_day_1)

    def _insert_item(self, project_id: int, description: str, item_type: str, start: datetime, worked_hours: float):
        timesheet, _created = Timesheet.objects.get_or_create(
            user=self.settings.user,
            month=start.month,
            year=start.year,
            project_id=project_id,
            status=Timesheet.Status.DRAFT,
        )
        timesheet.timesheetitem_set.create(
            date=start.date(), worked_hours=worked_hours, description=description, item_type=item_type
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
