"""Invoices app tests."""

import shutil
import tempfile
from datetime import date

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from apps.companies.models import Company
from apps.invoices.models import Invoice, InvoiceItem
from apps.relations.models import Relation

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class InvoicesTest(TestCase):
    """Invoices model tests."""

    fixtures = ["companies", "relations", "invoices", "geo"]

    @classmethod
    def setUpTestData(cls):
        """Set up the test data."""
        cls.company = Company.objects.get(pk=1)
        cls.relation = Relation.objects.get(pk=1)
        cls.invoice = Invoice.objects.get(pk=1)
        cls.invoice_item = InvoiceItem.objects.get(pk=1)
        cls.invoice_2 = Invoice.objects.get(pk=2)
        cls.invoice_3 = Invoice.objects.get(pk=3)  # Draft invoice 1 item
        cls.invoice_4 = Invoice.objects.get(pk=4)  # Draft invoice no items

    def test_model_content(self):
        """Test the model content."""
        # Persisted fields
        self.assertEqual(self.invoice.number, "0001")
        self.assertEqual(self.invoice.date, date(2025, 1, 1))
        self.assertEqual(self.invoice.company, self.company)
        self.assertEqual(self.invoice.relation, self.relation)
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)
        # Calculated fields
        self.assertEqual(self.invoice.date_due, date(2025, 2, 28))
        self.assertEqual(self.invoice.payment_communication, "+++002/0250/00187+++")
        self.assertEqual(self.invoice.subtotal, 200)
        self.assertEqual(self.invoice.vat_amount, 42)
        self.assertEqual(self.invoice.total, 242)

        # Persisted fields
        self.assertEqual(self.invoice_item.description, "[DUMMY] Service")
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
        self.assertEqual(str(self.invoice), "2025/0001: 242.00 (IDA Inc.->Dummy Customer) Due: 2025-02-28")

    def test_invoice_item_str(self):
        """Test the invoice item string representation."""
        self.assertEqual(str(self.invoice_item), "[DUMMY] Service 2.00x100.00 (21%) = 242.00")

    def test_invoice_date_due(self):
        """Test the invoice date due."""
        self.assertEqual(self.invoice.date.year, 2025)
        self.assertEqual(self.invoice.date.month, 1)
        self.assertEqual(self.invoice.date_due, date(2025, 2, 28))

        self.assertEqual(self.invoice_2.date.year, 2025)
        self.assertEqual(self.invoice_2.date.month, 12)
        self.assertEqual(self.invoice_2.date_due, date(2026, 1, 31))

    def test_invoice_payment_communication(self):
        """Test the invoice payment communication."""
        self.assertEqual(self.invoice.date.year, 2025)
        self.assertEqual(self.invoice.number, "0001")
        self.assertEqual(self.invoice.payment_communication, "+++002/0250/00187+++")

        self.assertEqual(self.invoice_2.date.year, 2025)
        self.assertEqual(self.invoice_2.number, "0002")
        self.assertEqual(self.invoice_2.payment_communication, "+++002/0250/00288+++")

        self.assertEqual(self.invoice_3.status, Invoice.Status.DRAFT)
        self.assertEqual(self.invoice_3.payment_communication, "")

    def test_invoice_number_calculated_once(self):
        """Test that the invoice number is only calculated once."""
        self.assertEqual(self.invoice.number, "0001")
        self.invoice.save()
        self.assertEqual(self.invoice.number, "0001")

    def test_invoice_confirm(self):
        """Test the invoice confirm method."""
        self.assertEqual(self.invoice.status, Invoice.Status.CONFIRMED)
        self.invoice.confirm()

        self.assertEqual(self.invoice_3.number, "")
        self.invoice_3.confirm()
        self.assertEqual(self.invoice_3.status, Invoice.Status.CONFIRMED)
        self.assertEqual(self.invoice_3.number, "0001")  # Should be the first of 2026

        with self.assertRaises(ValidationError) as context:
            self.invoice_4.confirm()
        self.assertEqual(context.exception.code, "no_items")

        self.invoice_4.invoiceitem_set.create(description="Test", unit_price=100, quantity=1, vat_percentage=21)
        self.assertGreater(self.invoice_3.date, self.invoice_4.date)  # Ensure invoice_3 is currently later than 4
        with self.assertRaises(ValidationError) as context:
            self.invoice_4.confirm()
        self.assertEqual(context.exception.code, "invalid_date")

        self.invoice_4.date = self.invoice_3.date
        self.invoice_4.confirm()
        self.assertEqual(self.invoice_4.status, Invoice.Status.CONFIRMED)
        self.assertEqual(self.invoice_4.number, "0002")  # Should be the second of 2026

    def test_invoice_create_pdf(self):
        """Test the invoice create PDF method."""
        # Ensure it's not possible to create pdf for draft invoices
        self.invoice.status = Invoice.Status.DRAFT
        self.invoice.save()
        self.assertFalse(self.invoice.pdf_file)

        with self.assertRaises(ValidationError) as context:
            self.invoice.create_pdf()
        self.assertEqual(context.exception.code, "invalid_status")

        self.invoice.status = Invoice.Status.CONFIRMED
        self.invoice.save()
        self.invoice.create_pdf()
        self.assertTrue(self.invoice.pdf_file)

        company_test = Company.objects.create(name="Test", vat_number="BE0123456789")
        self.invoice_2.company = company_test
        relation_test = Relation.objects.create(name="Test")
        self.invoice_2.relation = relation_test
        self.invoice_2.save()
        with self.assertRaises(ValidationError) as context:
            self.invoice_2.create_pdf()
        self.assertEqual(context.exception.code, "no_address")

        company_test.address_set.create(line1="Test 1", city="Test", postal_code="1234", country="BE")
        with self.assertRaises(ValidationError) as context:
            self.invoice_2.create_pdf()
        self.assertEqual(context.exception.code, "no_bank_account")

        company_test.bankaccount_set.create(iban="BE0123456789", bic="GEBABEBB", name="Test")
        with self.assertRaises(ValidationError) as context:
            self.invoice_2.create_pdf()
        self.assertEqual(context.exception.code, "no_address")

        relation_test.address_set.create(line1="Test 2", city="Test", postal_code="1234", country="BE")
        self.invoice_2.create_pdf()
        self.assertTrue(self.invoice_2.pdf_file)

    def test_invoice_send_by_email(self):
        """Test the invoice send by email method."""
        self.assertEqual(len(mail.outbox), 0)

        self.invoice.status = Invoice.Status.DRAFT
        self.invoice.save()
        with self.assertRaises(ValidationError) as context:
            self.invoice.send_by_email()
        self.assertEqual(context.exception.code, "invalid_status")

        self.invoice.status = Invoice.Status.CONFIRMED
        self.invoice.save()
        self.assertFalse(self.invoice.relation.email)
        with self.assertRaises(ValidationError) as context:
            self.invoice.send_by_email()
        self.assertEqual(context.exception.code, "no_email")

        self.invoice.relation.email = "dummy@example.com"
        self.invoice.relation.save()
        self.invoice.send_by_email()
        self.assertEqual(self.invoice.status, Invoice.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(mail.outbox[0].subject, "Invoice #VK/2025/0001 - IDA Inc.")
        self.assertEqual(mail.outbox[0].to, [self.invoice.relation.email])

        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[0].attachments[0][0], "invoices/ida_inc_invoice_2025_0001.pdf")

        with self.assertRaises(ValidationError) as context:
            self.invoice.send_by_email(even_if_already_sent=False)
        self.assertEqual(context.exception.code, "already_sent")
        self.assertEqual(len(mail.outbox), 1)

        self.invoice.send_by_email(even_if_already_sent=True)
        self.assertEqual(self.invoice.status, Invoice.Status.SENT)
        self.assertEqual(len(mail.outbox), 2)

    def test_invoice_item_to_dict(self):
        """Test the invoice item to dictionary method."""
        self.assertEqual(
            self.invoice_item.to_dict(),
            {"Description": "[DUMMY] Service", "Quantity": 2, "Unit price": 100, "VAT": "21%", "Subtotal": "200.00"},
        )

    def tearDown(self):
        """Clean up files after the test to avoid polluting storage."""
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
