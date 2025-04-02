"""Invoices models."""

import calendar
from pathlib import Path
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
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

    class Status(models.TextChoices):
        """Define the status choices."""

        DRAFT = "draft", _("Draft")
        CONFIRMED = "confirmed", _("Confirmed")
        SENT = "sent", _("Sent")
        PAID = "paid", _("Paid")

    number = models.CharField(verbose_name=_("number"), max_length=10, editable=False)
    date = models.DateField(verbose_name=_("date"))
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, verbose_name=_("company"))
    relation = models.ForeignKey("relations.Relation", on_delete=models.CASCADE, verbose_name=_("relation"))
    status = models.CharField(
        verbose_name=_("status"), max_length=10, choices=Status.choices, default=Status.DRAFT, editable=False
    )
    pdf_file = models.FileField(verbose_name=_("PDF file"), upload_to="invoices", blank=True, null=True)

    def __str__(self):
        """Return the string representation of the invoice."""
        return (
            f"{self.date.year}/{self.number}: {self.total:.2f} ({self.company}->{self.relation}) Due: {self.date_due}"
        )

    @property
    def date_due(self):
        """Calculate the due date for the invoice."""
        year = self.date.year
        month = self.date.month + 1
        if month > 12:
            year += 1
            month = 1

        last_day = calendar.monthrange(year, month)[1]
        return self.date.replace(year=year, month=month, day=last_day)

    @property
    def payment_communication(self):
        """Calculate the payment communication for the invoice.

        The payment is a structured payment communication that is used to identify the payment.

        Reference: https://nl.wikipedia.org/wiki/Gestructureerde_mededeling
        """
        if not self.number:
            return ""
        first_ten = f"{self.date.year}{self.number}".zfill(10)
        check_number = int(first_ten) % 97 or 97
        check_digits = str(check_number).zfill(2)
        return f"+++{first_ten[0:3]}/{first_ten[3:7]}/{first_ten[7:]}{check_digits}+++"

    @property
    def subtotal(self):
        """Calculate the subtotal."""
        return sum(item.subtotal for item in self.invoiceitem_set.all())

    @property
    def total(self):
        """Calculate the total."""
        return sum(item.total for item in self.invoiceitem_set.all())

    @property
    def vat_amount(self):
        """Calculate the VAT amount."""
        return sum(item.vat_amount for item in self.invoiceitem_set.all())

    def save(self, *args, **kwargs):
        """Save the invoice.

        Generate the invoice number if the invoice is confirmed and the invoice number was not generated before.
        """
        if self.status == self.Status.CONFIRMED and not self.number:
            self.number = str(
                Invoice.objects.filter(company=self.company, date__year=self.date.year)
                .exclude(status=self.Status.DRAFT)
                .count()
                + 1
            ).zfill(4)
        return super().save(*args, **kwargs)

    def confirm(self):
        """Confirm the invoice.

        For non-draft invoices, this is a no-op.
        An invoice without invoice items cannot be confirmed.
        An invoice with a date that is before the last non-draft invoice cannot be confirmed.
        """
        if self.status != self.Status.DRAFT:
            return

        if not self.invoiceitem_set.exists():
            raise ValidationError(gettext("An invoice without invoice items cannot be confirmed"), code="no_items")

        last_non_draft = (
            Invoice.objects.filter(company=self.company).exclude(status=self.Status.DRAFT).order_by("-date").first()
        )
        if last_non_draft and last_non_draft.date > self.date:
            raise ValidationError(
                gettext(
                    "A non-draft invoice (date: %(last_date)s) exists after %(self_date)s. Update the date to at "
                    "least %(last_date)s."
                ),
                code="invalid_date",
                params={"last_date": last_non_draft.date, "self_date": self.date},
            )

        self.status = self.Status.CONFIRMED
        self.save()

    def create_pdf(self):
        """Create a PDF for the invoice."""
        if self.status != self.Status.CONFIRMED:
            raise ValidationError(
                gettext("Only confirmed invoices can have their PDF generated"), code="invalid_status"
            )
        with override(self.relation.language, deactivate=True):
            invoice_address = self._get_invoice_address()
            bank_account = self._get_bank_account()
            details_from = self._get_details_from(invoice_address, bank_account)
            relation_address = self._get_relation_address()
            details_to = self._get_details_to(relation_address)
            title = self._get_invoice_title()
            lines = [item.to_dict() for item in self.invoiceitem_set.all()]

            summary = self._get_summary()
            invoice_date = date_format(self.date, format="DATE_FORMAT")
            invoice_date_due = date_format(self.date_due, format="DATE_FORMAT")
            invoice_details = self._get_invoice_details(
                details_from, details_to, title, lines, summary, invoice_date, invoice_date_due
            )
            if self.company.logo:
                invoice_details.logo = self.company.logo.path
            if self.company.graphic_element:
                invoice_details.graphic_element = self.company.graphic_element.path
            cleaned_company_name = self.company.get_name_cleaned()
            name = f"{cleaned_company_name}_invoice_{self.date.year}_{self.number}.pdf"
            filename = self.pdf_file.field.generate_filename(self, name)
            invoice_path_str = default_storage.path(filename)
            invoice_path = Path(invoice_path_str)
            invoice_path.parent.mkdir(parents=True, exist_ok=True)
            invoice_pdf = pdf.invoice.InvoicePDF(invoice_details, pdf.invoice.PDFDetails(invoice_path_str))
            invoice_pdf.generate()
        self.pdf_file.name = f"{self.pdf_file.field.upload_to}/{name}"
        self.save()
        return name

    def send_by_email(self, even_if_already_sent: bool = False):
        """Send the invoice by email."""
        if self.status == self.Status.DRAFT:
            raise ValidationError(gettext("Draft invoices can not be sent by email"), code="invalid_status")
        if self.status == self.Status.SENT and not even_if_already_sent:
            raise ValidationError(gettext("Invoice has already been sent"), code="already_sent")
        if not self.relation.email:
            raise ValidationError(
                gettext("Relation (%(relation)s) has no email address"),
                code="no_email",
                params={"relation": self.relation},
            )
        if not self.pdf_file:
            self.create_pdf()
        email_message = EmailMessage(
            subject=f"{self._get_invoice_title()} - {self.company.name}",
            body="Please find attached the invoice.",
            from_email=self.company.email,
            to=[self.relation.email],
            attachments=[
                (
                    self.pdf_file.name,
                    Path(self.pdf_file.path).read_bytes(),
                )
            ],
        )
        mail_sent = email_message.send()
        if mail_sent:
            self.status = self.Status.SENT
            self.save()

    def _get_invoice_title(self):
        model_verbose_name = self._meta.verbose_name or type(self).__name__
        return f"{model_verbose_name.capitalize()} #VK/{self.date.year}/{self.number}"

    def _get_invoice_details(self, details_from, details_to, title, lines, summary, invoice_date, invoice_date_due):
        invoice_details = pdf.invoice.InvoiceDetails(
            details_from=details_from,
            details_to=details_to,
            title=title,
            date={self._meta.get_field("date").verbose_name.capitalize(): invoice_date},
            due_date={gettext("date due").capitalize(): invoice_date_due},
            payment_communication={gettext("payment communication").capitalize(): self.payment_communication},
            lines=lines,
            summary=summary,
        )
        return invoice_details

    def _get_summary(self):
        summary = {
            gettext("subtotal").capitalize(): f"{self.subtotal:.2f}",
            gettext("VAT").upper(): f"{self.vat_amount:.2f}",
            gettext("total").capitalize(): f"{self.total:.2f}",
        }
        return summary

    def _get_details_to(self, relation_address):
        details_to = pdf.invoice.DetailsTo(
            gettext("ATTN."),
            self.relation.name,
            relation_address.line1,
            f"{relation_address.postal_code} {relation_address.city}",
            relation_address.get_country_display(),  # type: ignore[reportAttributeAccessIssue]
            self.relation.get_vat_number_display(),
        )
        return details_to

    def _get_details_from(self, invoice_address, bank_account):
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
        return details_from

    def _get_relation_address(self):
        relation_address = self.relation.address_set.first()
        if not relation_address:
            raise ValidationError(gettext("Relation has no address"), code="no_address")
        return relation_address

    def _get_bank_account(self):
        bank_account = self.company.bankaccount_set.first()
        if not bank_account:
            raise ValidationError(gettext("Company has no bank account"), code="no_bank_account")
        return bank_account

    def _get_invoice_address(self):
        invoice_address = self.company.address_set.first()
        if not invoice_address:
            raise ValidationError(gettext("Company has no address"), code="no_address")
        return invoice_address

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
        return f"{self.description} {self.quantity}x{self.unit_price} ({int(self.vat_percentage)}%) = {self.total:.2f}"

    class Meta:
        """Set meta options."""

        verbose_name = _("invoice item")
        verbose_name_plural = _("invoice items")
