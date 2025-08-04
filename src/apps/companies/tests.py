"""Companies app tests."""

from django.test import TestCase

from apps.companies.models import BankAccount, Company


class CompanyTests(TestCase):
    """Company model tests."""

    fixtures = ["companies"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.company = Company.objects.get(pk=1)
        cls.bank_account = BankAccount.objects.get(pk=1)

    def test_model_content(self):
        """Test the model content."""
        self.assertEqual(self.company.name, "IDA Inc.")
        self.assertEqual(self.company.phone, "+32 490 12 34 56")
        self.assertEqual(self.company.email, "info@ida.com")
        self.assertEqual(self.company.website, "https://ida.com")
        self.assertEqual(self.company.vat_number, "BE0123456789")
        self.assertEqual(self.company.business_court, "Antwerpen, afd. Tongeren")

        self.assertEqual(self.bank_account.iban, "BE68539007547034")
        self.assertEqual(self.bank_account.bic, "BBRUBEBB")
        self.assertEqual(self.bank_account.name, "ING")
        self.assertEqual(self.bank_account.company, self.company)
        self.assertTrue(hasattr(self.company, "address_set"))
        self.assertTrue(hasattr(self.company, "bankaccount_set"))
        self.assertTrue(hasattr(self.company, "project_set"))
        self.assertTrue(hasattr(self.company, "user_set"))

    def test_get_vat_number_display(self):
        """Test the get_vat_number_display method."""
        self.assertEqual(self.company.get_vat_number_display(), "VAT BE0123456789")

    def test_get_name_cleaned(self):
        """Test the get_name_cleaned method."""
        self.assertEqual(self.company.get_name_cleaned(), "ida_inc")

    def test_str(self):
        """Test the string representation."""
        self.assertEqual(str(self.company), "IDA Inc.")
        self.assertEqual(str(self.bank_account), "ING BE68539007547034")
