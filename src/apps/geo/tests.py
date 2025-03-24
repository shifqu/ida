"""Geo app tests."""

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.companies.models import Company
from apps.geo.models import Address
from apps.relations.models import Relation


class GeoTests(TestCase):
    """Geo model tests."""

    fixtures = ["companies", "relations", "geo"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.company = Company.objects.get(pk=1)
        cls.address = Address.objects.get(pk=1)
        cls.relation = Relation.objects.get(pk=1)

    def test_model_content(self):
        """Test the model content."""
        self.assertEqual(self.address.line1, "Koning Albert I-laan 123")
        self.assertEqual(self.address.line2, "")
        self.assertEqual(self.address.line3, "")
        self.assertEqual(self.address.line4, "")
        self.assertEqual(self.address.postal_code, "1000")
        self.assertEqual(self.address.city, "Brussels")
        self.assertEqual(self.address.state_province_region, "")
        self.assertEqual(self.address.country, "BE")
        self.assertEqual(self.address.relation, None)
        self.assertEqual(self.address.company, self.company)

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.address), "Koning Albert I-laan 123\n1000 Brussels\nBelgium")

    def test_constraints(self):
        """Test the constraints."""
        address = Address(line1="Koning Albert I-laan 123", postal_code="1000", city="Brussels", country="BE")

        # Test case 1: no relation or company
        with transaction.atomic():
            with self.assertRaises(IntegrityError) as context:
                address.save()
            self.assertTrue("address_must_have_exactly_one_relation_or_company" in str(context.exception))

        # Test case 2: relation AND company
        address.company = self.company
        address.relation = self.relation
        with transaction.atomic():
            with self.assertRaises(IntegrityError) as context:
                address.save()
            self.assertTrue("address_must_have_exactly_one_relation_or_company" in str(context.exception))

        # Test case 3: company only
        address.relation = None
        address.save()

        # Test case 4: relation only
        address.company = None
        address.relation = self.relation
        address.save()
