"""Projects app tests."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.companies.models import Company
from apps.geo.models import Address
from apps.projects.models import Project, Rate
from apps.relations.models import Relation


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
