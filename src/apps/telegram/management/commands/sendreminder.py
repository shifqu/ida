"""Django command to send a reminder to active users with a chat_id."""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import translation
from django.utils.translation import gettext as _

from apps.telegram.models import TelegramSettings


class Command(BaseCommand):
    """Send a reminder via telegram."""

    help = "Send a reminder to the configured chat_id to remind them to register work."

    def handle(self, *_args, **_options):
        """Send a text message to the user to remind them to register work.

        References:
        https://core.telegram.org/bots/api#sendmessage

        Note:
        The chat_id is configured on the user as a TelegramSetting.
        The bot is assumed to handle the /registerwork command
        """
        reply_button = [{"text": "/registerwork"}]
        reply_markup = {"keyboard": [reply_button], "resize_keyboard": False, "one_time_keyboard": False}
        root_url = settings.TELEGRAM["BOT_URL"].rstrip("/")
        endpoint = f"{root_url}/sendMessage"
        for setting in TelegramSettings.objects.filter(user__is_active=True):
            translation.activate(setting.user.language)
            text = _("Do not forget to register your work today!")
            translation.deactivate()
            args = {"chat_id": setting.chat_id, "text": text, "reply_markup": reply_markup}
            response = requests.post(endpoint, json=args, timeout=5)
            response_json = response.json()
            if not response_json.get("ok"):
                self.stderr.write(self.style.ERROR(f"Something went wrong while sending the reminder. {response_json}"))
                raise CommandError(f"Failed to send reminder to {setting.user}.")
            self.stdout.write(self.style.SUCCESS(f"Successfully sent the reminder to {setting.user}."))
