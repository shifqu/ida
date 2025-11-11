"""Timesheets app tests."""

from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django_telegram_app.bot import get_commands, load_command_class
from django_telegram_app.bot.testing.testcases import TelegramBotTestCase
from django_telegram_app.resolver import get_telegram_settings_model

from apps.projects.models import Project
from apps.timesheets.models import TimeRangeItemTypeRule, Timesheet, TimesheetItem, WeekdayItemTypeRule
from apps.timesheets.telegrambot.steps import InsertTimesheetItems


class TimesheetsTests(TestCase):
    """Timesheets model tests."""

    fixtures = ["companies", "relations", "users", "timesheets", "projects"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.timesheet = Timesheet.objects.get(pk=1)
        cls.user = get_user_model().objects.get(pk=1)
        cls.project = Project.objects.get(pk=1)

    def test_model_content(self):
        """Test the model content."""
        self.assertEqual(self.timesheet.month, 1)
        self.assertEqual(self.timesheet.year, 2025)
        self.assertEqual(self.timesheet.status, "draft")
        self.assertEqual(self.timesheet.user, self.user)
        self.assertEqual(self.timesheet.project, self.project)

        timesheet_item = self.timesheet.timesheetitem_set.first()
        assert timesheet_item is not None, "Timesheet item should not be None"
        self.assertEqual(timesheet_item.item_type, TimesheetItem.ItemType.STANDARD)
        self.assertEqual(str(timesheet_item.date), "2025-01-01")
        self.assertEqual(timesheet_item.worked_hours, 8.0)
        self.assertEqual(timesheet_item.description, "dummy description")

    def test_name(self):
        """Test the name property."""
        self.assertEqual(self.timesheet.name, "Dummy Project - Dummy User - 01/2025")

    def test_get_missing_days(self):
        """Test the get_missing_days method."""
        missing_days = self.timesheet.get_missing_days()
        self.assertEqual(len(missing_days), 20)

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.timesheet), "Dummy Project - Dummy User - 01/2025")

    def test_timesheet_item_str(self):
        """Test the string representation."""
        timesheet_item = self.timesheet.timesheetitem_set.first()
        self.assertEqual(str(timesheet_item), "2025-01-01 - Standard - 8.0 hours (dummy description)")
        timesheet_item = self.timesheet.timesheetitem_set.filter(item_type=TimesheetItem.ItemType.NIGHT).first()
        self.assertEqual(str(timesheet_item), "2025-01-03 - Night - 2.0 hours")

    def test_timesheet_unique_together(self):
        """Test the unique together constraint."""
        self.timesheet.mark_as_completed()
        self.assertEqual(self.timesheet.status, Timesheet.Status.COMPLETED)

        with self.assertRaises(ValidationError) as cm:
            Timesheet.objects.get_or_create(
                user=self.timesheet.user,
                month=self.timesheet.month,
                year=self.timesheet.year,
                status=Timesheet.Status.DRAFT,
                project_id=self.timesheet.project.pk,
            )
        self.assertIn("already exists", str(cm.exception))

        with self.assertRaises(Timesheet.DoesNotExist) as cm:
            Timesheet.objects.get(
                user=self.timesheet.user,
                month=self.timesheet.month,
                year=self.timesheet.year,
                status=Timesheet.Status.DRAFT,
                project_id=self.timesheet.project.pk,
            )

    def test_timesheet_overview(self):
        """Test the timesheet overview generation."""
        overview = self.timesheet.get_overview()
        expected_summary_overview = (
            "Totals for Dummy Project - Dummy User - 01/2025:\n"
            "- 16.0 hours (Standard)\n"
            "- 8.0 hours (On call)\n"
            "- 2.0 hours (Night)"
        )
        self.assertEqual(overview, expected_summary_overview)

        detailed_overview = self.timesheet.get_overview(include_details=True)
        expected_detailed_overview = (
            "Detailed Timesheet Overview for Dummy Project - Dummy User - 01/2025:\n"
            "2025-01-01 - Standard - 8.0 hours (dummy description)\n"
            "2025-01-02 - Standard - 8.0 hours\n"
            "2025-01-06 - Standard - 0.0 hours (holiday epiphany)\n"
            "2025-01-01 - On call - 8.0 hours\n"
            "2025-01-03 - Night - 2.0 hours\n\n"
            "Totals for Dummy Project - Dummy User - 01/2025:\n"
            "- 16.0 hours (Standard)\n"
            "- 8.0 hours (On call)\n"
            "- 2.0 hours (Night)"
        )
        self.assertEqual(detailed_overview, expected_detailed_overview)

    def test_timesheet_holidays_overview(self):
        """Test the timesheet holidays overview generation."""
        overview = self.timesheet.get_holidays_overview()
        expected_summary_overview = "Holidays Overview for Dummy Project - Dummy User - 01/2025:\n2025-01-06"
        self.assertEqual(overview, expected_summary_overview)


class TimesheetsTelegramBotTestCase(TelegramBotTestCase):
    """Timesheets telegram bot tests."""

    fixtures = ["companies", "relations", "users", "timesheets", "projects"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        super().setUpTestData()
        cls.timesheet = Timesheet.objects.get(pk=1)
        cls.user = get_user_model().objects.get(pk=1)
        cls.project = Project.objects.get(pk=1)
        cls.telegram_setting = get_telegram_settings_model().objects.create(user=cls.user, chat_id=123456789)

    def test_telegram_registerwork(self):
        """Test the telegram registerwork command."""
        existing_timesheet_items = self.timesheet.timesheetitem_set.count()
        self.send_text("/registerwork")
        self.click_on_text("➡️ Next")
        self.click_on_text("⬅️ Back")
        self.click_on_text("Dummy Project: 2025-01-03")
        self.click_on_text("⬅️ Previous step")
        self.click_on_text("Dummy Project: 2025-01-03")
        self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items)
        self.click_on_text("Full day (8h)")
        self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items + 1)

    def test_telegram_editwork(self):
        """Test the telegram editwork command."""
        existing_timesheet_items = self.timesheet.timesheetitem_set.count()
        timesheet_item = TimesheetItem.objects.get(timesheet=self.timesheet, date=datetime(2025, 1, 2).date())
        self.assertEqual(timesheet_item.worked_hours, 8.0)
        self.send_text("/editwork")
        self.click_on_text("Dummy Project: 2025-01-02 (8.0h)")
        self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items)
        self.click_on_text("Holiday (0h)")
        self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items)
        timesheet_item.refresh_from_db()
        self.assertEqual(timesheet_item.worked_hours, 0.0)

    def test_telegram_registerovertime(self):
        """Test the telegram registerovertime command."""
        fixed_now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("django.utils.timezone.now", return_value=fixed_now):
            existing_timesheet_items = self.timesheet.timesheetitem_set.count()
            self.send_text("/registerovertime")
            self.click_on_text("(01)")
            self.send_text("1630")
            self.click_on_text("⬅️ Previous step")  # Force to select date and time again
            self.click_on_text("(01)")
            self.send_text("1830")  # Changing start time due to previous step back
            self.click_on_text("(01)")
            self.send_text("2030")
            self.send_text("test description")
            self.click_on_text("⬅️ Previous step")  # Force to select/send description again
            self.send_text("dummy description")
            self.click_on_text("Night")
            self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items)
            self.click_on_text("✅ Ok")
            self.assertEqual(self.timesheet.timesheetitem_set.count(), existing_timesheet_items + 1)

    def test_telegram_registerovertime_select_previous_month(self):
        """Test selecting the previous month for the telegram registerovertime command."""
        fixed_now = datetime(2025, 3, 31, 0, 0, 0, tzinfo=timezone.utc)
        with patch("django.utils.timezone.now", return_value=fixed_now):
            existing_timesheets = Timesheet.objects.count()
            self.send_text("/registerovertime")
            self.click_on_text("<<")
            self.click_on_text("01")
            self.send_text("1630")
            self.click_on_text("01")
            self.send_text("2030")
            self.send_text("test description")
            self.click_on_text("Night")
            self.assertEqual(Timesheet.objects.count(), existing_timesheets)
            self.click_on_text("✅ Ok")
            self.assertEqual(Timesheet.objects.count(), existing_timesheets + 1)
            timesheet_2025_02 = Timesheet.objects.get(month=2, year=2025)
            self.assertEqual(timesheet_2025_02.timesheetitem_set.count(), 1)

    def test_telegram_complete_timesheet(self):
        """Test the telegram complete timesheet command."""
        year = 2024  # The fixture defines a timesheet for 2025 already
        timesheet_1 = Timesheet.objects.create(user=self.user, project=self.project, month=1, year=year)
        timesheet_2 = Timesheet.objects.create(user=self.user, project=self.project, month=2, year=2025)

        self.assertEqual(timesheet_1.status, Timesheet.Status.DRAFT)
        self.send_text("/completetimesheet")
        self.click_on_text(str(timesheet_1))
        self.click_on_text("❌ Cancel")
        timesheet_1.refresh_from_db()  # The instance could be updated indirectly, so we refresh it.
        self.assertEqual(timesheet_1.status, Timesheet.Status.DRAFT)
        self.assertIn("Command canceled", self.fake_bot_post.call_args[1]["payload"]["text"])

        self.assertEqual(timesheet_1.status, Timesheet.Status.DRAFT)
        self.send_text("/completetimesheet")
        self.click_on_text(str(timesheet_1))
        self.click_on_text("✅ Ok")
        timesheet_1.refresh_from_db()  # The instance is updated indirectly, so we refresh it.
        self.assertEqual(timesheet_1.status, Timesheet.Status.COMPLETED)

        # Still two left, confirm timesheet_2
        self.assertEqual(timesheet_2.status, Timesheet.Status.DRAFT)
        self.send_text("/completetimesheet")
        self.click_on_text(str(timesheet_2))
        self.click_on_text("✅ Ok")
        timesheet_2.refresh_from_db()  # The instance is updated indirectly, so we refresh it.
        self.assertEqual(timesheet_2.status, Timesheet.Status.COMPLETED)

        # Only one left, should go for completion immediately
        timesheet_0 = Timesheet.objects.get(pk=1)
        self.assertEqual(timesheet_0.status, Timesheet.Status.DRAFT)
        self.send_text("/completetimesheet")
        self.click_on_text("✅ Ok")
        timesheet_0.refresh_from_db()  # The instance is updated indirectly, so we refresh it.
        self.assertEqual(timesheet_0.status, Timesheet.Status.COMPLETED)

    def test_prepare_item_batches(self):
        """Test the prepare item batches method."""
        commands = get_commands()
        registerovertime_name = "registerovertime"
        registerovertime_info = commands[registerovertime_name]
        register_overtime_cmd = load_command_class(registerovertime_info, registerovertime_name, self.telegram_setting)
        insert_timesheet_items_step = InsertTimesheetItems(register_overtime_cmd)
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
        data = dict(
            project_id=self.project.pk,
            project_name=self.project.name,
            start_time="2025-01-01T17:30:00",
            end_time="2025-01-02T08:00:00",
            description="Test Overtime",
            item_type=0,
            item_type_label="Inferred",
        )
        items = insert_timesheet_items_step._prepare_item_batches(data)
        expected_key = (1, 2025, self.project.pk)
        self.assertIn(expected_key, items)
        self.assertEqual(len(items[expected_key]), 4)
        self.assertEqual(sum(item.worked_hours for item in items[expected_key]), 14.5)

        rule3 = WeekdayItemTypeRule(
            item_type=TimesheetItem.ItemType.SUNDAY,
            weekday=6,
        )
        rule3.save()
        data_2 = dict(
            project_id=self.project.pk,
            project_name=self.project.name,
            start_time="2025-01-05T22:00:00",
            end_time="2025-01-06T02:00:00",
            description="Test Overtime",
            item_type=0,
            item_type_label="Inferred",
        )
        items_2 = insert_timesheet_items_step._prepare_item_batches(data_2)
        self.assertEqual(len(items_2[expected_key]), 2)
        self.assertEqual(sum(item.worked_hours for item in items_2[expected_key]), 4)
        self.assertEqual(items_2[expected_key][0].item_type, TimesheetItem.ItemType.SUNDAY)
        self.assertEqual(items_2[expected_key][1].item_type, TimesheetItem.ItemType.NIGHT)

    def test_request_overview_summary(self):
        """Test the request overview command in summary mode."""
        self.send_text("/requestoverview")
        self.click_on_text("Summary Overview")
        expected_overview = (
            "Totals for Dummy Project - Dummy User - 01/2025:\n"
            "- 16.0 hours (Standard)\n"
            "- 8.0 hours (On call)\n"
            "- 2.0 hours (Night)"
        )
        self.assertEqual(self.fake_bot_post.call_args[1]["payload"]["text"], expected_overview)

    def test_request_overview_detailed(self):
        """Test the request overview command in detailed mode."""
        self.send_text("/requestoverview")
        self.click_on_text("Detailed Overview")
        expected_overview = (
            "Detailed Timesheet Overview for Dummy Project - Dummy User - 01/2025:\n"
            "2025-01-01 - Standard - 8.0 hours (dummy description)\n"
            "2025-01-02 - Standard - 8.0 hours\n"
            "2025-01-06 - Standard - 0.0 hours (holiday epiphany)\n"
            "2025-01-01 - On call - 8.0 hours\n"
            "2025-01-03 - Night - 2.0 hours\n"
            "\n"
            "Totals for Dummy Project - Dummy User - 01/2025:\n"
            "- 16.0 hours (Standard)\n"
            "- 8.0 hours (On call)\n"
            "- 2.0 hours (Night)"
        )
        self.assertEqual(self.fake_bot_post.call_args[1]["payload"]["text"], expected_overview)

    def test_request_overview_holidays(self):
        """Test the request overview command in holidays mode."""
        self.send_text("/requestoverview")
        self.click_on_text("Holidays Overview")
        expected_overview = "Holidays Overview for Dummy Project - Dummy User - 01/2025:\n2025-01-06"
        self.assertEqual(self.fake_bot_post.call_args[1]["payload"]["text"], expected_overview)

    def test_startregisterwork(self):
        """Test the start register work command."""
        out = StringIO()

        call_command("startregisterwork", stdout=out, force=True)
        self.assertEqual(self.fake_bot_post.call_count, 1)
        self.assertEqual(self.fake_bot_post.call_args.args[0], "sendMessage")
        self.assertIn("Started the command for", out.getvalue())

        # Confirm timesheets and run command again, this should result in "no missing days"
        self.timesheet.status = Timesheet.Status.COMPLETED
        self.timesheet.save()
        self.fake_bot_post.reset_mock()
        out = StringIO()
        call_command("startregisterwork", stdout=out, force=True)
        self.assertTrue(self.fake_bot_post.called)
        self.assertIn("No days found. Unable to complete", self.fake_bot_post.call_args[1]["payload"]["text"])
