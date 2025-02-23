"""Relations app tests module."""

from django.test import TestCase

from apps.relations.models import Relation


class RelationTests(TestCase):
    """Relation model tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.relation = Relation.objects.create(
            name="Test Relation",
            category=Relation.Category.CUSTOMER,
            language="en",
            phone="+32 490 12 34 56",
        )

    def test_model_content(self):
        """Test the model content."""
        self.assertEqual(self.relation.name, "Test Relation")
        self.assertEqual(self.relation.category, Relation.Category.CUSTOMER)
        self.assertEqual(self.relation.language, "en")
        self.assertEqual(self.relation.phone, "+32 490 12 34 56")
        self.assertEqual(self.relation.email, "")
        self.assertEqual(self.relation.website, "")
        self.assertEqual(self.relation.vat_number, "")
        self.assertEqual(self.relation.bank_account_number, "")

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.relation), "Test Relation")
