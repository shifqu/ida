"""Companies models."""

import re
from typing import TYPE_CHECKING

from django.db import models
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """Represent a company."""

    if TYPE_CHECKING:
        from apps.geo.models import Address
        from apps.projects.models import Project
        from apps.users.models import IdaUser

        address_set: models.Manager[Address]
        bankaccount_set: models.Manager["BankAccount"]
        project_set: models.Manager[Project]
        user_set: models.Manager[IdaUser]

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
    logo = models.ImageField(verbose_name=_("logo"), upload_to="companies/logos/", blank=True, null=True)
    graphic_element = models.ImageField(
        verbose_name=_("graphic element"), upload_to="companies/graphic_elements/", blank=True, null=True
    )

    def __str__(self):
        """Return the string representation of the company."""
        return self.name

    def get_vat_number_display(self):
        """Return the VAT number for display."""
        vat_str = _("VAT")
        return f"{vat_str} {self.vat_number}"

    def get_name_cleaned(self):
        """Return the cleaned name.

        All non-alphanumeric characters are replaced with an underscore and consecutive underscore are replaced by a
        single underscore.
        The final result is stripped of leading and trailing underscores and lowercased.
        """
        cleaned_name = re.sub(r"[^a-zA-Z0-9]", "_", self.name)
        cleaned_name = re.sub(r"__+", "_", cleaned_name)
        cleaned_name = cleaned_name.strip("_")
        return cleaned_name.lower()

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
