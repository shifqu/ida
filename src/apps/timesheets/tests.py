"""Timesheets app tests."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.projects.models import Project
from apps.timesheets.models import Timesheet


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
        self.assertEqual(timesheet_item.item_type, "standard")
        self.assertEqual(str(timesheet_item.date), "2025-01-01")
        self.assertEqual(timesheet_item.worked_hours, 8.0)
        self.assertEqual(timesheet_item.description, "")

    def test_name(self):
        """Test the name property."""
        self.assertEqual(self.timesheet.name, "Dummy Project - Dummy User - 01/2025")

    def test_get_missing_days(self):
        """Test the get_missing_days method."""
        missing_days = self.timesheet.get_missing_days()
        self.assertEqual(len(missing_days), 21)

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.timesheet), "Dummy Project - Dummy User - 01/2025")

    def test_timesheet_item_str(self):
        """Test the string representation."""
        timesheet_item = self.timesheet.timesheetitem_set.first()
        self.assertEqual(str(timesheet_item), "2025-01-01 - 8.0 hours ()")

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
