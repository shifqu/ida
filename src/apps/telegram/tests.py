"""Telegram tests."""

from datetime import datetime, timezone
from io import StringIO
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.projects.models import Project
from apps.telegram.bot.commands.registerovertime import OvertimeData
from apps.telegram.bot.commands.utils import get_command_cls
from apps.telegram.models import TelegramSettings, TimeRangeItemTypeRule, WeekdayItemTypeRule
from apps.timesheets.models import Timesheet, TimesheetItem
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
        cls.url = reverse("webhook")

    def test_telegram_invalid_token(self):
        """Test the telegram app with an invalid token."""
        response = self.client.post(
            self.url,
            data={},
            headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_token"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"status": "error", "message": "Invalid token."})

    def test_telegram_send_help(self):
        """Test the telegram send help command."""
        bot_post = patch("apps.telegram.bot.core.Bot.post", MagicMock()).start()
        self._send_text("dummy text")
        self.assertEqual(bot_post.call_count, 1)
        self.assertEqual(bot_post.call_args.args[0], "sendMessage")
        self.assertIn("I am IDA", bot_post.call_args[1]["payload"]["text"])

    def test_telegram_registerwork(self):
        """Test the telegram registerwork command."""
        existing_timesheet_items = self.timesheet.timesheetitem_set.count()
        bot_post = patch("apps.telegram.bot.core.Bot.post", MagicMock()).start()
        self._send_text("/registerwork")
        self._click_on_text("➡️ Next", bot_post)
        self._click_on_text("⬅️ Back", bot_post)
        self._click_on_text("Dummy Project: 2025-01-03", bot_post)
        self._click_on_text("⬅️ Back", bot_post)
        self._click_on_text("Dummy Project: 2025-01-03", bot_post)
        self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items)
        self._click_on_text("Full day (8h)", bot_post)
        self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items + 1)

    def test_telegram_registerovertime(self):
        """Test the telegram registerovertime command."""
        fixed_now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("django.utils.timezone.now", return_value=fixed_now):
            existing_timesheet_items = self.timesheet.timesheetitem_set.count()
            bot_post = patch("apps.telegram.bot.core.Bot.post", MagicMock()).start()
            self._send_text("/registerovertime")
            self._click_on_text("(01)", bot_post)
            self._send_text("1630")
            self._click_on_text("(01)", bot_post)
            self._send_text("1830")
            self._send_text("test")
            self._click_on_text("Night", bot_post)
            self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items)
            self._click_on_text("yes", bot_post)
            self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items + 1)

    def test_startregisterwork(self):
        """Test the start register work command."""
        bot_post = patch("apps.telegram.bot.core.Bot.post", MagicMock()).start()
        out = StringIO()
        call_command("startregisterwork", stdout=out)
        self.assertEqual(bot_post.call_count, 1)
        self.assertEqual(bot_post.call_args.args[0], "sendMessage")
        self.assertIn("Started the command for", out.getvalue())

        # Confirm timesheets and run command again, this should result in "no missing days"
        self.timesheet.status = Timesheet.Status.COMPLETED
        self.timesheet.save()
        bot_post.reset_mock()
        out = StringIO()
        call_command("startregisterwork", stdout=out)
        self.assertTrue(bot_post.called)
        self.assertIn("No missing days", bot_post.call_args[1]["payload"]["text"])

    def test_prepare_item_batches(self):
        """Test the prepare item batches method."""
        register_overtime_cmd = get_command_cls("/registerovertime")(self.telegram_setting)
        rule1 = TimeRangeItemTypeRule(
            item_type=TimesheetItem.ItemType.STANDARD,
            start_time="07:00",
            end_time="19:30",
        )
        rule1.save()
        rule2 = TimeRangeItemTypeRule(
            item_type=TimesheetItem.ItemType.NIGHT,
            start_time="19:30",
            end_time="07:00",
        )
        rule2.save()
        step_data = OvertimeData(
            project_id=self.project.pk,
            project_name=self.project.name,
            start_time=datetime(2025, 1, 1, 17, 30, 0),
            end_time=datetime(2025, 1, 2, 8, 0, 0),
            description="Test Overtime",
        )
        items = register_overtime_cmd._prepare_item_batches(step_data)
        expected_key = (1, 2025, self.project.pk)
        self.assertIn(expected_key, items)
        self.assertEqual(len(items[expected_key]), 4)
        self.assertEqual(sum(item.worked_hours for item in items[expected_key]), 14.5)

        rule3 = WeekdayItemTypeRule(
            item_type=TimesheetItem.ItemType.SUNDAY,
            weekday=6,
        )
        rule3.save()
        step_data_2 = OvertimeData(
            project_id=self.project.pk,
            project_name=self.project.name,
            start_time=datetime(2025, 1, 5, 22, 0, 0),
            end_time=datetime(2025, 1, 6, 2, 0, 0),
            description="Test Overtime",
        )
        items_2 = register_overtime_cmd._prepare_item_batches(step_data_2)
        self.assertEqual(len(items_2[expected_key]), 2)
        self.assertEqual(sum(item.worked_hours for item in items_2[expected_key]), 4)
        self.assertEqual(items_2[expected_key][0].item_type, TimesheetItem.ItemType.SUNDAY)
        self.assertEqual(items_2[expected_key][1].item_type, TimesheetItem.ItemType.NIGHT)

    def _click_on_text(self, text: str, bot_post: MagicMock):
        """Simulate a click on the specified text button."""
        inline_keyboard = bot_post.call_args[1]["payload"]["reply_markup"]["inline_keyboard"]
        callback_data = [item for row in inline_keyboard for item in row if item["text"] == text][0]["callback_data"]
        data = construct_telegram_callback_query(callback_data)
        response = self._post(data)
        return response

    def _send_text(self, text: str, verify: bool = True):
        """Simulate sending a text message."""
        payload = construct_telegram_update(text)
        return self._post(payload, verify=verify)

    def _post(self, data: dict, verify: bool = True):
        response = self.client.post(
            self.url,
            data=data,
            headers={"X-Telegram-Bot-Api-Secret-Token": settings.TELEGRAM["WEBHOOK_TOKEN"]},
            content_type="application/json",
        )
        if verify:
            self.assertEqual(response.json(), {"status": "ok", "message": "Message received."})
        return response


def construct_telegram_update(message_text: str):
    """Construct a minimal telegram update."""
    return {"message": {"chat": {"id": 123456789}, "text": message_text}}


def construct_telegram_callback_query(callback_data: str):
    """Construct a minimal telegram callback query."""
    return {
        "callback_query": {
            "message": {
                "message_id": 537,
                "chat": {"id": 123456789, "first_name": "test", "type": "private"},
            },
            "data": callback_data,
        },
    }
