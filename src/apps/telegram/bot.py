"""Telegram bot module."""

import enum
from datetime import datetime

import requests
from django.conf import settings

from apps.telegram.models import TelegramSettings
from apps.timesheets.models import Timesheet, TimesheetItem


class Commands(enum.Enum):
    """Represent the available commands handled by the bot."""

    START = "/start"  # TODO: Implement the start command
    REGISTERWORK = "/registerwork"
    DAY = "day"
    OPTION = "option"
    PAGE = "page"


class Bot:
    """Telegram bot."""

    @classmethod
    def post(cls, endpoint: str, payload: dict, timeout: int = 5):
        """Post the payload to the given endpoint."""
        url = cls.construct_endpoint(endpoint)
        response = requests.post(url, json=payload, timeout=timeout)
        return response

    @classmethod
    def handle(cls, update: dict):
        """Handle the update."""
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            cmd = Commands(text)
            if cmd is Commands.REGISTERWORK:
                cls.display_missing_days(chat_id)
        elif "callback_query" in update:
            query = update["callback_query"]
            message_id = query["message"]["message_id"]
            chat_id = query["message"]["chat"]["id"]
            data: str = query["data"]
            text = data.split("_", 1)[0]
            cmd = Commands(text)
            if cmd is Commands.DAY:
                cls.show_day_options(chat_id, message_id, data)
            elif cmd is Commands.OPTION:
                cls.register_option(chat_id, message_id, data)
            elif cmd is Commands.PAGE:
                cls.show_page(chat_id, message_id, data)

    @classmethod
    def show_page(cls, chat_id: int, message_id: int, data: str):
        """Show the next or previous page of missing days."""
        page = int(data.split("_", 1)[1])
        start = (page - 1) * 4
        end = start + 4
        days = cls._get_missing_days()
        keyboard = [[{"text": day, "callback_data": f"day_{day}"}] for day in days[start:end]]
        if page > 1:
            keyboard.append([{"text": "⬅️ Back", "callback_data": f"page_{page - 1}"}])
        if len(days) > end:
            keyboard.append([{"text": "➡️ Next", "callback_data": f"page_{page + 1}"}])
        reply_markup = {"inline_keyboard": keyboard}
        cls.edit_message(message_id, "Select a day:", chat_id, reply_markup=reply_markup)

    @classmethod
    def register_option(cls, chat_id: int, message_id: int, data: str):
        """Register the work for the given day and option."""
        _, day, option = data.split("_", 2)
        cls._registerwork(day, option, chat_id)
        cls.edit_message(message_id, f"{day}: {option} registered.", chat_id)

    @classmethod
    def show_day_options(cls, chat_id: int, message_id: int, data: str):
        """Show the options for the given day."""
        day = data.split("_", 1)[1]
        options = cls._get_day_options()
        keyboard = [[{"text": option, "callback_data": f"option_{day}_{option}"}] for option in options]
        keyboard.append([{"text": "⬅️ Back", "callback_data": "page_1"}])
        reply_markup = {"inline_keyboard": keyboard}
        cls.edit_message(message_id, f"Options for {day}:", chat_id, reply_markup=reply_markup)

    @classmethod
    def display_missing_days(cls, chat_id: int):
        """Display the missing days to the user.

        This is the first step in the registerwork process.
        """
        days = cls._get_missing_days()
        keyboard = [[{"text": day, "callback_data": f"day_{day}"}] for day in days]
        if len(keyboard) > 4:
            keyboard = keyboard[:4]
            keyboard.append([{"text": "➡️ Next", "callback_data": "page_2"}])
        reply_markup = {"inline_keyboard": keyboard}
        cls.send_message("Select a day:", chat_id, reply_markup=reply_markup)

    @staticmethod
    def valid_token(token: str):
        """Validate the token.

        If no token is configured, the token is considered valid.
        """
        if not settings.TELEGRAM["WEBHOOK_TOKEN"]:
            return True
        return token == settings.TELEGRAM["WEBHOOK_TOKEN"]

    @staticmethod
    def construct_endpoint(name: str):
        """Construct the endpoint for the given command."""
        root_url = settings.TELEGRAM["BOT_URL"].rstrip("/")
        return f"{root_url}/{name}"

    @classmethod
    def send_message(cls, text: str, chat_id: int, reply_markup: dict | None = None):
        """Send a message to the user.

        References:
        https://core.telegram.org/bots/api#sendmessage
        """
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        cls.post("sendMessage", payload=payload)

    @classmethod
    def edit_message(cls, message_id: int, text: str, chat_id: int, reply_markup: dict | None = None):
        """Edit a message.

        References:
        https://core.telegram.org/bots/api#editmessagetext
        """
        payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        cls.post("editMessageText", payload=payload)

    @staticmethod
    def _get_available_types():
        """Get the available types."""
        return TimesheetItem.ItemType.choices

    @staticmethod
    def _get_missing_days():
        """Get the missing days.

        Only monday through friday are considered.
        """
        draft_timesheets = Timesheet.objects.filter(status=Timesheet.Status.DRAFT)
        return [str(date) for timesheet in draft_timesheets for date in timesheet.missing_days]

    @staticmethod
    def _get_day_options():
        """Get the options for the day."""
        return ["0h", "4h", "8h", "16h", "24h"]

    @staticmethod
    def _registerwork(date_str: str, option: str, chat_id: int):
        """Register the work."""
        hours = option.lower().replace("h", "")
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        setting = TelegramSettings.objects.get(chat_id=chat_id)
        timesheet = Timesheet.objects.get(
            status=Timesheet.Status.DRAFT, month=date_obj.month, year=date_obj.year, user=setting.user
        )
        timesheet.timesheetitem_set.create(date=date_str, worked_hours=hours)
