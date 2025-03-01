"""Companies models."""

from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """Represents a company."""

    if TYPE_CHECKING:
        from apps.geo.models import Address

        address_set: models.Manager["Address"]
        bankaccount_set: models.Manager["BankAccount"]

    name = models.CharField(verbose_name=_("name"), max_length=255)
    phone = models.CharField(
        verbose_name=_("phone"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Phone number with country code (eg. +32 490 12 34 56)"),
    )
    email = models.EmailField(verbose_name=_("email"), max_length=255, blank=True, default="")
    website = models.URLField(verbose_name=_("website"), max_length=255, blank=True, default="")
    vat_number = models.CharField(verbose_name=_("VAT number"), max_length=255, blank=True, default="")
    business_court = models.CharField(
        verbose_name=_("business court"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Example: Antwerpen, afd. Hasselt"),
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

        verbose_name = _("company")
        verbose_name_plural = _("companies")


class BankAccount(models.Model):
    """Represent a bank account."""

    iban = models.CharField(verbose_name=_("IBAN"), max_length=34)
    bic = models.CharField(verbose_name=_("BIC"), max_length=11, blank=True, default="")
    name = models.CharField(verbose_name=_("name"), max_length=255, blank=True, default="")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name=_("company"))

    def __str__(self):
        """Return the string representation of the bank account."""
        return f"{self.name} {self.iban}"

    class Meta:
        """Set meta options."""

        verbose_name = _("bank account")
        verbose_name_plural = _("bank accounts")
