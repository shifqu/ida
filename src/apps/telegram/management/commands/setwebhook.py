"""Django command to set a telegram webhook."""

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Set a telegram webhook."""

    help = "Sets the webhook for the telegram bot."

    def handle(self, *_args, **_options):
        """Set a webhook.

        Notes: Once a webhook is set, getUpdates no longer works.

        References: https://core.telegram.org/bots/api#setwebhook
        """
        root_url = settings.TELEGRAM["BOT_URL"].rstrip("/")
        endpoint = f"{root_url}/setWebhook"
        parts = [settings.DOMAIN_NAME, settings.TELEGRAM["ROOT_URL"], settings.TELEGRAM["WEBHOOK_URL"]]
        url = "/".join(part.strip("/") for part in parts if part)
        args = {"url": url}
        if settings.TELEGRAM["WEBHOOK_TOKEN"]:
            args["secret_token"] = settings.TELEGRAM["WEBHOOK_TOKEN"]
        response = requests.post(endpoint, json=args, timeout=5)
        response_json: dict = response.json()
        if not response_json.get("ok"):
            self.stderr.write(self.style.ERROR(f"Something went wrong while setting the webhook. {response_json}"))
            raise CommandError("Failed to set webhook.")
        self.stdout.write(self.style.SUCCESS(f'Successfully set webhook to "{url}"'))
