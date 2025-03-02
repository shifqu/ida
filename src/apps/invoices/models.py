"""Invoices models."""

import calendar
from typing import TYPE_CHECKING

from django.db import models
from django.utils.formats import date_format
from django.utils.translation import gettext, override
from django.utils.translation import gettext_lazy as _

import pdf.invoice


class Invoice(models.Model):
    """Represent an invoice."""

    if TYPE_CHECKING:
        from apps.companies.models import Company
        from apps.relations.models import Relation

        company: models.ForeignKey["Company"]
        relation: models.ForeignKey["Relation"]
        invoiceitem_set: models.Manager["InvoiceItem"]

    number = models.CharField(verbose_name=_("number"), max_length=255, editable=False)
    date = models.DateField(verbose_name=_("date"))
    date_due = models.DateField(verbose_name=_("date due"), editable=False)
    payment_communication = models.CharField(verbose_name=_("payment communication"), max_length=255, editable=False)
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, verbose_name=_("company"))
    relation = models.ForeignKey("relations.Relation", on_delete=models.CASCADE, verbose_name=_("relation"))

    def __str__(self):
        """Return the string representation of the invoice."""
        return (
            f"{self.date.year}/{self.number}: {self.total:.2f} ({self.company}->{self.relation}) Due: {self.date_due}"
        )

    @property
    def subtotal(self):
        """Calculate the subtotal."""
        return sum(item.subtotal for item in self.invoiceitem_set.all())

    @property
    def vat_amount(self):
        """Calculate the VAT amount."""
        return sum(item.vat_amount for item in self.invoiceitem_set.all())

    @property
    def total(self):
        """Calculate the total."""
        return sum(item.total for item in self.invoiceitem_set.all())

    def save(self, *args, **kwargs):
        """Save the invoice.

        This function also generates the invoice number and due date.
        """
        self.full_clean()
        if not self.number:  # Only calculate once
            self.number = str(Invoice.objects.filter(date__year=self.date.year).count() + 1).zfill(4)
        self.date_due = self._get_due_date()
        self.payment_communication = self._get_payment_communication()
        return super().save(*args, **kwargs)

    def _get_payment_communication(self):
        """Get the payment communication for the invoice.

        The payment is a structured payment communication that is used to identify the payment.

        Reference: https://nl.wikipedia.org/wiki/Gestructureerde_mededeling
        """
        first_ten = f"{self.date.year}{self.number}".zfill(10)
        check_number = int(first_ten) % 97 or 97
        check_digits = str(check_number).zfill(2)
        return f"+++{first_ten[0:3]}/{first_ten[3:7]}/{first_ten[7:]}{check_digits}+++"

    def _get_due_date(self):
        """Get the due date for the invoice."""
        year = self.date.year
        month = self.date.month + 1
        if month > 12:
            year += 1
            month = 1

        last_day = calendar.monthrange(year, month)[1]
        return self.date.replace(year=year, month=month, day=last_day)

    def create_pdf(self):
        """Create a PDF for the invoice."""
        with override(self.relation.language, deactivate=True):
            invoice_address = self.company.address_set.first()
            if not invoice_address:
                raise ValueError("Company has no address")
            bank_account = self.company.bankaccount_set.first()
            if not bank_account:
                raise ValueError("Company has no bank account")
            details_from = pdf.invoice.DetailsFrom(
                self.company.name,
                invoice_address.line1,
                f"{invoice_address.postal_code} {invoice_address.city}",
                invoice_address.get_country_display(),  # type: ignore[reportAttributeAccessIssue]
                self.company.website,
                self.company.email,
                self.company.business_court,
                self.company.get_vat_number_display(),
                str(bank_account),
            )
            relation_address = self.relation.address_set.first()
            if not relation_address:
                raise ValueError("Relation has no address")
            details_to = pdf.invoice.DetailsTo(
                gettext("ATTN."),
                self.relation.name,
                relation_address.line1,
                f"{relation_address.postal_code} {relation_address.city}",
                relation_address.get_country_display(),  # type: ignore[reportAttributeAccessIssue]
                self.relation.get_vat_number_display(),
            )
            invoice_number = str(self.number).zfill(4)
            model_verbose_name = self._meta.verbose_name or type(self).__name__
            title = f"{model_verbose_name.capitalize()} #VK/{self.date.year}/{invoice_number}"
            lines = [item.to_dict() for item in self.invoiceitem_set.all()]

            summary = {
                gettext("subtotal").capitalize(): f"{self.subtotal:.2f}",
                gettext("VAT").upper(): f"{self.vat_amount:.2f}",
                gettext("total").capitalize(): f"{self.total:.2f}",
            }
            invoice_date = date_format(self.date, format="DATE_FORMAT")
            invoice_date_due = date_format(self.date_due, format="DATE_FORMAT")
            invoice_details = pdf.invoice.InvoiceDetails(
                details_from=details_from,
                details_to=details_to,
                title=title,
                date={self._meta.get_field("date").verbose_name.capitalize(): invoice_date},
                due_date={self._meta.get_field("date_due").verbose_name.capitalize(): invoice_date_due},
                payment_communication={
                    self._meta.get_field("payment_communication").verbose_name.capitalize(): self.payment_communication
                },
                lines=lines,
                summary=summary,
            )
            if self.company.logo:
                invoice_details.logo = self.company.logo.path
            if self.company.graphic_element:
                invoice_details.graphic_element = self.company.graphic_element.path
            name = f"{self.company.name.replace(' ', '_').lower()}_invoice_{self.date.year}_{invoice_number}.pdf"
            invoice_pdf = pdf.invoice.InvoicePDF(
                invoice_details,
                pdf.invoice.PDFDetails(name),
            )
            invoice_pdf.generate()

    class Meta:
        """Set meta options."""

        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")


class InvoiceItem(models.Model):
    """Represent an invoice item."""

    description = models.CharField(verbose_name=_("description"), max_length=255)
    unit_price = models.DecimalField(verbose_name=_("unit price"), max_digits=10, decimal_places=2)
    quantity = models.DecimalField(verbose_name=_("quantity"), max_digits=10, decimal_places=2)
    vat_percentage = models.DecimalField(
        verbose_name=_("VAT"), max_digits=5, decimal_places=2, help_text=_("VAT percentage")
    )
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, verbose_name=_("invoice"))

    @property
    def subtotal(self):
        """Calculate the subtotal."""
        return self.unit_price * self.quantity

    @property
    def vat_amount(self):
        """Calculate the VAT amount."""
        return self.subtotal * self.vat_percentage / 100

    @property
    def total(self):
        """Calculate the total."""
        return self.subtotal + self.vat_amount

    def to_dict(self):
        """Return the invoice item as a dictionary."""
        return {
            self._meta.get_field("description").verbose_name.capitalize(): self.description,
            self._meta.get_field("quantity").verbose_name.capitalize(): self.quantity,
            self._meta.get_field("unit_price").verbose_name.capitalize(): self.unit_price,
            self._meta.get_field("vat_percentage").verbose_name.upper(): f"{int(self.vat_percentage)}%",
            gettext("subtotal").capitalize(): f"{self.subtotal:.2f}",
        }

    def __str__(self):
        """Return the string representation of the invoice item."""
        return f"{self.description} {self.quantity}x{self.unit_price} ({int(self.vat_amount)}%) = {self.total:.2f}"

    class Meta:
        """Set meta options."""

        verbose_name = _("invoice item")
        verbose_name_plural = _("invoice items")
