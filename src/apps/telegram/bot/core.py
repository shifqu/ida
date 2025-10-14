"""Telegram bot core module."""

import requests
from django.conf import settings

from apps.telegram.bot.commands.utils import get_command_cls
from apps.telegram.bot.types import TelegramUpdate
from apps.telegram.models import CallbackData, TelegramSettings

DO_NOTHING = "noop"


class Bot:
    """Represent the Telegram bot."""

    @staticmethod
    def validate_token(token: str | None):
        """Validate the webhook token.

        If no token is configured, the token is considered valid.

        Note:
            This token is not the CallbackData token but a token used to validate the webhook.
            This enables us to differentiate original telegram requests from spam
        """
        if not settings.TELEGRAM["WEBHOOK_TOKEN"]:
            return True
        return token == settings.TELEGRAM["WEBHOOK_TOKEN"]

    @classmethod
    def handle(cls, update: dict):
        """Handle the update."""
        telegram_update = TelegramUpdate(update)
        telegram_settings = TelegramSettings.objects.get(chat_id=telegram_update.chat_id)

        if telegram_update.is_command():
            cls._start_command_or_send_help(telegram_update, telegram_settings)
        elif telegram_update.is_callback_query():
            cls._call_command_step(telegram_update.callback_data, telegram_settings, telegram_update)
        elif telegram_settings.data.get("waiting_for"):
            token = telegram_settings.data["waiting_for"]
            cls._call_command_step(token, telegram_settings, telegram_update)
        else:
            cls.send_help(telegram_update.chat_id)

    @classmethod
    def send_help(cls, chat_id: int):
        """Send a help message to the user."""
        help_text = (
            "I am IDA, I can help you register hours and manage timesheeting/invoicing.\n"
            "\n"
            "Currently available commands:\n"
            "/registerwork - Register work hours\n"
            "/registerovertime - Register overtime hours\n"
            "/completetimesheet - Mark a timesheet as completed\n"
        )
        cls.send_message(help_text, chat_id)

    @classmethod
    def send_message(cls, text: str, chat_id: int, reply_markup: dict | None = None, message_id: int = 0):
        """Send a message to the user.

        If message_id is provided, it will edit the existing message instead.

        References:
        https://core.telegram.org/bots/api#sendmessage
        """
        payload = {"chat_id": chat_id, "text": text}
        endpoint = "sendMessage"
        if message_id:
            payload["message_id"] = message_id
            endpoint = "editMessageText"

        if reply_markup:
            payload["reply_markup"] = reply_markup
        cls.post(endpoint, payload=payload)

    @classmethod
    def post(cls, endpoint: str, payload: dict, timeout: int = 5):
        """Post the payload to the given endpoint."""
        url = cls._construct_endpoint(endpoint)
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response

    @staticmethod
    def _construct_endpoint(name: str):
        """Construct the endpoint for the given command."""
        root_url = settings.TELEGRAM["BOT_URL"].rstrip("/")
        return f"{root_url}/{name}"

    @classmethod
    def _start_command_or_send_help(cls, telegram_update: TelegramUpdate, telegram_settings: TelegramSettings):
        """Start a command or send help message."""
        command_name = telegram_update.message_text.split(maxsplit=1)[0]
        try:
            command_cls = get_command_cls(command_name)
        except KeyError:
            cls.send_help(telegram_update.chat_id)
            return
        command_cls(telegram_settings).start(telegram_update)

    @classmethod
    def _call_command_step(cls, token: str, telegram_settings: TelegramSettings, telegram_update: TelegramUpdate):
        """Call a command's step from the provided data."""
        if token == DO_NOTHING:
            return

        try:
            data = CallbackData.objects.get(token=token)
        except CallbackData.DoesNotExist as exc:
            cls.send_message(
                "This command has expired.", telegram_update.chat_id, message_id=telegram_update.message_id
            )
            raise ValueError("This command has expired.") from exc

        command_cls = get_command_cls(data.command)
        command = command_cls(telegram_settings)
        getattr(command, data.step)(telegram_update)
