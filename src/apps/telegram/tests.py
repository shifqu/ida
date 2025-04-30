"""Telegram tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from apps.relations.models import Relation
from apps.telegram.bot import Bot
from apps.telegram.models import TelegramSettings
from apps.timesheets.models import Timesheet
from apps.users.models import IdaUser


class TelegramTestCase(TestCase):
    """Telegram test case."""

    fixtures = ["relations"]

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.user = IdaUser.objects.create_user(username="test", password="test", is_superuser=False)
        cls.telegram_setting = TelegramSettings.objects.create(user=cls.user, chat_id=123456789)
        cls.relation = Relation.objects.get(pk=1)
        cls.timesheet = Timesheet.objects.create(
            name="Test Timesheet", month=1, year=2025, relation=cls.relation, user=cls.user
        )

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
        fixture_file = Path(__file__).parent / "fixtures" / "messages.json"
        fixtures: list = json.loads(fixture_file.read_text())
        url = reverse("webhook")
        bot_post = patch("apps.telegram.bot.Bot.post", MagicMock()).start()
        for i, fixture in enumerate(fixtures):
            response = self.client.post(
                url,
                fixture["fields"]["raw_message"],
                headers={"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM["WEBHOOK_TOKEN"]},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "message": "Message received."}, f"fixture {i=} failed.")
            expected_payload = _construct_expected_payload(i, fixtures, bot_post)
            if expected_payload:
                self.assertDictEqual(bot_post.call_args[1], expected_payload)
                self.assertEqual(self.timesheet.timesheetitem_set.count(), 0)
            else:
                # No payload means it's the final payload
                self.assertEqual(bot_post.call_args[1]["payload"]["text"], "Thanks, your action was registered")
                self.assertEqual(self.timesheet.timesheetitem_set.count(), 1)


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
    payload = {"chat_id": message["chat"]["id"], "text": message["text"], "parse_mode": Bot.parse_mode}
    if "reply_markup" in message:
        payload["reply_markup"] = message["reply_markup"]
    if bot_post.call_args[0][0] == "editMessageText":
        payload["message_id"] = message["message_id"]
    return {"payload": payload}
