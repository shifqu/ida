"""Relations app tests module."""

from django.test import TestCase

from apps.relations.models import Relation


class RelationTests(TestCase):
    """Relation model tests."""

    fixtures = ["relations"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.customer = Relation.objects.get(pk=1)

    def test_model_content(self):
        """Test the model content."""
        self.assertEqual(self.customer.name, "Dummy Customer")
        self.assertEqual(self.customer.category, Relation.Category.CUSTOMER)
        self.assertEqual(self.customer.language, "en")
        self.assertEqual(self.customer.phone, "")
        self.assertEqual(self.customer.email, "")
        self.assertEqual(self.customer.website, "")
        self.assertEqual(self.customer.vat_number, "")
        self.assertEqual(self.customer.bank_account_number, "")

    def test_get_vat_number_display(self):
        """Test the get_vat_number_display method."""
        self.assertEqual(self.customer.get_vat_number_display(), "")
        self.customer.vat_number = "BE0123456789"
        self.assertEqual(self.customer.get_vat_number_display(), "VAT BE0123456789")

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.customer), "Dummy Customer")
