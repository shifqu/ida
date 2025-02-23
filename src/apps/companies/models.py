"""Companies models."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """Represents a company."""

    name = models.CharField(max_length=255)
    phone = models.CharField(
        max_length=255, blank=True, default="", help_text=_("Phone number with country code (eg. +32 490 12 34 56)")
    )
    email = models.EmailField(max_length=255, blank=True, default="")
    website = models.URLField(max_length=255, blank=True, default="")
    vat_number = models.CharField(max_length=255, blank=True, default="", help_text=_("VAT number"))
    business_court = models.CharField(
        max_length=255, blank=True, default="", help_text=_("Business court (eg. Antwerpen, afd. Hasselt)")
    )

    def __str__(self):
        """Return the string representation of the company."""
        return self.name

    def get_vat_number_display(self):
        """Return the VAT number for display."""
        vat_str = _("VAT")
        return f"{vat_str} {self.vat_number}"

    class Meta:
        """Add a correct plural name."""

        verbose_name_plural = "Companies"


class BankAccount(models.Model):
    """Represent a bank account."""

    iban = models.CharField(max_length=34)
    bic = models.CharField(max_length=11, blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")
    company = models.ForeignKey(Company, on_delete=models.CASCADE)

    def __str__(self):
        """Return the string representation of the bank account."""
        return f"{self.name} {self.iban}"
