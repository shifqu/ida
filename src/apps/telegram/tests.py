"""Telegram tests."""

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.projects.models import Project
from apps.telegram.models import TelegramSettings
from apps.timesheets.models import Timesheet
from apps.users.models import IdaUser


class TelegramTestCase(TestCase):
    """Telegram test case."""

    fixtures = ["users", "companies", "relations", "projects", "telegramsettings", "timesheets"]

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = IdaUser.objects.get(pk=1)
        cls.telegram_setting = TelegramSettings.objects.get(pk=1)
        cls.project = Project.objects.get(pk=1)
        cls.timesheet = Timesheet.objects.get(pk=1)
        cls.fixture_file = Path(__file__).parent / "fixtures" / "messages.json"
        cls.fixtures: list = json.loads(cls.fixture_file.read_text())

    def test_telegram_invalid_token(self):
        """Test the telegram app with an invalid token."""
        url = reverse("webhook")
        response = self.client.post(
            url,
            data={},
            headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_token"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"status": "error", "message": "Invalid token."})

    def test_telegram(self):
        """Test the telegram app."""
        self.maxDiff = None
        url = reverse("webhook")
        bot_post = patch("apps.telegram.bot.Bot.post", MagicMock()).start()
        for i, fixture in enumerate(self.fixtures):
            response = self.client.post(
                url,
                fixture["fields"]["raw_message"],
                headers={"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM["WEBHOOK_TOKEN"]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "message": "Message received."}, f"fixture {i=} failed.")
            expected_payload = _construct_expected_payload(i, self.fixtures, bot_post)
            if expected_payload:
                self.assertDictEqual(bot_post.call_args[1], expected_payload)
                self.assertEqual(self.timesheet.timesheetitem_set.count(), 0)
            else:
                # No payload means it's the final payload
                self.assertEqual(bot_post.call_args[1]["payload"]["text"], "2025-01-07: 8h registered.")
                self.assertEqual(self.timesheet.timesheetitem_set.count(), 1)

    def test_display_missing_days(self):
        """Test the display missing days command."""
        bot_post = patch("apps.telegram.bot.Bot.post", MagicMock()).start()
        out = StringIO()
        call_command("displaymissingdays", stdout=out)
        self.assertEqual(bot_post.call_count, 1)
        self.assertEqual(bot_post.call_args.args[0], "sendMessage")
        expected_payload = _construct_expected_payload(0, self.fixtures, bot_post)
        self.assertEqual(bot_post.call_args.kwargs, expected_payload)
        self.assertIn("Successfully sent the message", out.getvalue())

        # Confirm timesheets and run command again, this should result in "no missing days"
        self.timesheet.status = Timesheet.Status.COMPLETED
        self.timesheet.save()
        bot_post.reset_mock()
        out = StringIO()
        call_command("displaymissingdays", stdout=out)
        self.assertFalse(bot_post.called, "Bot should not post when no days are missing.")
        self.assertIn("No missing days", out.getvalue())


def _construct_expected_payload(idx: int, fixtures: list[dict], bot_post: MagicMock):
    """Construct the expected payload."""
    try:
        next_fixture = fixtures[idx + 1]
    except IndexError:
        return None
    raw_message = next_fixture["fields"]["raw_message"]
    if "callback_query" in raw_message:
        message = raw_message["callback_query"]["message"]
    else:
        message = raw_message["message"]
    payload = {"chat_id": message["chat"]["id"], "text": message["text"]}
    if "reply_markup" in message:
        payload["reply_markup"] = message["reply_markup"]
    if bot_post.call_args[0][0] == "editMessageText":
        payload["message_id"] = message["message_id"]
    return {"payload": payload}
