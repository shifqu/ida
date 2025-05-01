"""Telegram bot module."""

import enum
import logging
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

    parse_mode = "MarkdownV2"

    @classmethod
    def post(cls, endpoint, payload, timeout=5):
        """Post the payload to the given endpoint."""
        url = cls.construct_endpoint(endpoint)
        response = requests.post(url, json=payload, timeout=timeout)
        logging.info(f"Telegram: POST {url} {payload} -> {response.status_code} {response.json()}")
        return response

    @classmethod
    def handle(cls, update: dict):
        """Handle the update."""
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]
            cmd = Commands(text)
            if cmd is Commands.REGISTERWORK:
                days = cls._get_missing_days()
                keyboard = [[{"text": day, "callback_data": f"day_{day}"}] for day in days]
                if len(keyboard) > 4:
                    keyboard = keyboard[:4]
                    keyboard.append([{"text": "➡️ Next", "callback_data": "page_2"}])
                reply_markup = {"inline_keyboard": keyboard}
                cls.send_message("Select a day:", chat_id, reply_markup=reply_markup)

        elif "callback_query" in update:
            query = update["callback_query"]
            message_id = query["message"]["message_id"]
            chat_id = query["message"]["chat"]["id"]
            data: str = query["data"]
            text = data.split("_", 1)[0]
            cmd = Commands(text)

            if cmd is Commands.DAY:
                day = data.split("_", 1)[1]
                options = cls._get_day_options()
                keyboard = [[{"text": option, "callback_data": f"option_{day}_{option}"}] for option in options]
                keyboard.append([{"text": "⬅️ Back", "callback_data": "page_1"}])
                reply_markup = {"inline_keyboard": keyboard}
                cls.edit_message(message_id, f"Options for {day}:", chat_id, reply_markup=reply_markup)

            elif cmd is Commands.OPTION:
                _, day, option = data.split("_", 2)
                option = option.lower().replace("h", "")
                cls._registerwork(day, option, chat_id)
                cls.edit_message(message_id, "Thanks, your action was registered", chat_id)

            elif cmd is Commands.PAGE:
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

    @staticmethod
    def valid_token(token):
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
    def send_message(cls, text, chat_id, reply_markup=None):
        """Send a message to the user.

        References:
        https://core.telegram.org/bots/api#sendmessage
        """
        payload = {
            "chat_id": chat_id,
            "text": text,
            # "parse_mode": cls.parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        cls.post("sendMessage", payload=payload)

    @classmethod
    def edit_message(cls, message_id, text, chat_id, reply_markup=None):
        """Edit a message.

        References:
        https://core.telegram.org/bots/api#editmessagetext
        """
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            # "parse_mode": cls.parse_mode,
        }
        if reply_markup:
            # payload["reply_markup"] = {"inline_keyboard": keyboard}
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
    def _registerwork(date_str, option, chat_id):
        """Register the work."""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        setting = TelegramSettings.objects.get(chat_id=chat_id)
        timesheet = Timesheet.objects.get(
            status=Timesheet.Status.DRAFT, month=date_obj.month, year=date_obj.year, user=setting.user
        )
        timesheet.timesheetitem_set.create(date=date_str, worked_hours=option)
