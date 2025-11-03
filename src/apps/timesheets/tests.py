"""Timesheets app tests."""

from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.projects.models import Project
from apps.timesheets.models import Timesheet, TimesheetItem


class TimesheetsTests(TestCase):
    """Timesheets model tests."""

    fixtures = ["companies", "relations", "users", "timesheets", "projects", "telegramsettings"]

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

    def test_startregisterwork(self):
        """Test the start register work command."""
        bot_post = patch("apps.telegram.bot.Bot.post", MagicMock()).start()
        out = StringIO()

        call_command("startregisterwork", stdout=out, force=True)
        self.assertEqual(bot_post.call_count, 1)
        self.assertEqual(bot_post.call_args.args[0], "sendMessage")
        self.assertIn("Started the command for", out.getvalue())

        # Confirm timesheets and run command again, this should result in "no missing days"
        self.timesheet.status = Timesheet.Status.COMPLETED
        self.timesheet.save()
        bot_post.reset_mock()
        out = StringIO()
        call_command("startregisterwork", stdout=out, force=True)
        self.assertTrue(bot_post.called)
        self.assertIn("No days found. Unable to complete", bot_post.call_args[1]["payload"]["text"])
