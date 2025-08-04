"""Projects app tests."""

from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.companies.models import Company
from apps.projects.models import Project, Rate
from apps.relations.models import Relation
from apps.timesheets.models import Timesheet


class ProjectsTests(TestCase):
    """Projects model tests."""

    fixtures = ["companies", "relations", "users", "projects"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.project = Project.objects.get(pk=1)
        cls.user = get_user_model().objects.get(pk=1)

    def test_model_content(self):
        """Test the model content."""
        self.assertEqual(self.project.name, "Dummy Project")
        self.assertEqual(self.project.description, "A project for testing purposes")
        self.assertEqual(str(self.project.start_date), "2025-01-01")
        self.assertEqual(str(self.project.end_date), "2025-12-31")
        self.assertTrue(self.project.users.contains(self.user))  # type: ignore
        self.assertEqual(self.project.relation, Relation.objects.get(pk=1))
        self.assertEqual(self.project.company, Company.objects.get(pk=1))
        self.assertEqual(self.project.invoice_line_prefix, "Dummy Prefix")
        for rate in Rate.objects.all():
            self.assertTrue(self.project.rate_set.contains(rate))

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.project), "Dummy Project")

    def test_rate_str(self):
        """Test the string representation."""
        expected_str = "Dummy Project - standard: 500.00 x 21.00% (daily)"
        self.assertEqual(str(self.project.rate_set.first()), expected_str)

    def test_createinvoices(self):
        """Test the createinvoices management command."""
        out = StringIO()
        with self.assertRaises(CommandError) as cm:
            call_command("createinvoices", project_id=999, month=1, year=2025, stdout=out)
        self.assertIn("Project with id 999 does not exist.", str(cm.exception))

        out = StringIO()
        call_command("createinvoices", month=1, year=2025, stdout=out)
        self.assertIn("No completed timesheets found", out.getvalue())

        timesheet = Timesheet.objects.create(
            user=self.user,
            project=self.project,
            month=1,
            year=2025,
            status="completed",
        )
        out = StringIO()
        call_command("createinvoices", month=1, year=2025, stdout=out)
        self.assertIn("No invoice items created", out.getvalue())

        timesheet.timesheetitem_set.create(
            item_type="standard",
            date="2025-01-01",
            worked_hours=8.0,
            description="Worked on project tasks",
        )
        timesheet.status = Timesheet.Status.COMPLETED
        timesheet.save()
        out = StringIO()
        call_command("createinvoices", month=1, year=2025, stdout=out)
        self.assertIn("Created invoice for Dummy Project - Dummy User - 01/2025.", out.getvalue())
