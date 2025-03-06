"""Invoices app tests."""

from datetime import date

from django.test import TestCase

from apps.companies.models import Company
from apps.invoices.models import Invoice, InvoiceItem
from apps.relations.models import Relation


class InvoicesTest(TestCase):
    """Invoices model tests."""

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.company = Company.objects.create(
            name="IDA Inc.",
            phone="+32 490 12 34 56",
            email="info@ida.com",
            website="https://ida.com",
            vat_number="BE0123456789",
            business_court="Antwerpen, afd. Tongeren",
        )
        cls.relation = Relation.objects.create(name="John Doe", category=Relation.Category.CUSTOMER)
        cls.invoice = Invoice.objects.create(date="2025-01-01", company=cls.company, relation=cls.relation)
        cls.invoice_item = InvoiceItem.objects.create(
            invoice=cls.invoice, description="Test", quantity=2, unit_price=100, vat_percentage=21
        )
        cls.invoice_2 = Invoice.objects.create(date="2025-12-01", company=cls.company, relation=cls.relation)

    def test_model_content(self):
        """Test the model content."""
        # Persisted fields
        self.assertEqual(self.invoice.number, "0001")
        self.assertEqual(self.invoice.date, date(2025, 1, 1))
        self.assertEqual(self.invoice.date_due, date(2025, 2, 28))
        self.assertEqual(self.invoice.payment_communication, "+++002/0250/00187+++")
        self.assertEqual(self.invoice.company, self.company)
        self.assertEqual(self.invoice.relation, self.relation)
        # Calculated fields
        self.assertEqual(self.invoice.subtotal, 200)
        self.assertEqual(self.invoice.vat_amount, 42)
        self.assertEqual(self.invoice.total, 242)

        # Persisted fields
        self.assertEqual(self.invoice_item.description, "Test")
        self.assertEqual(self.invoice_item.unit_price, 100)
        self.assertEqual(self.invoice_item.quantity, 2)
        self.assertEqual(self.invoice_item.invoice, self.invoice)
        self.assertEqual(self.invoice_item.vat_percentage, 21)
        # Calculated fields
        self.assertEqual(self.invoice_item.subtotal, 200)
        self.assertEqual(self.invoice_item.vat_amount, 42)
        self.assertEqual(self.invoice_item.total, 242)

    def test_invoice_str(self):
        """Test the invoice string representation."""
        self.assertEqual(str(self.invoice), "2025/0001: 242.00 (IDA Inc.->John Doe) Due: 2025-02-28")

    def test_invoice_item_str(self):
        """Test the invoice item string representation."""
        self.assertEqual(str(self.invoice_item), "Test 2x100 (21%) = 242.00")

    def test_invoice_date_due(self):
        """Test the invoice date due."""
        self.assertEqual(self.invoice_2.date.year, 2025)
        self.assertEqual(self.invoice_2.date.month, 12)
        self.assertEqual(self.invoice_2.date_due, date(2026, 1, 31))

    def test_invoice_payment_communication(self):
        """Test the invoice payment communication."""
        self.assertEqual(self.invoice_2.date.year, 2025)
        self.assertEqual(self.invoice_2.number, "0002")
        self.assertEqual(self.invoice_2.payment_communication, "+++002/0250/00288+++")

    def test_invoice_number_calculated_once(self):
        """Test that the invoice number is only calculated once."""
        self.assertEqual(self.invoice.number, "0001")
        self.invoice.save()
        self.assertEqual(self.invoice.number, "0001")

    def test_invoice_item_to_dict(self):
        """Test the invoice item to dictionary method."""
        self.assertEqual(
            self.invoice_item.to_dict(),
            {
                "Description": "Test",
                "Quantity": 2,
                "Unit price": 100,
                "VAT": "21%",
                "Subtotal": "200.00",
            },
        )
