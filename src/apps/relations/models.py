"""Relations models."""

from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Relation(models.Model):
    """Represent a relation."""

    if TYPE_CHECKING:
        from apps.geo.models import Address

        address_set: models.Manager["Address"]

    class Category(models.TextChoices):
        """Represent the relation type choices."""

        CUSTOMER = "CUSTOMER", _("Customer")
        SUPPLIER = "SUPPLIER", _("Supplier")

    name = models.CharField(verbose_name=_("name"), max_length=255)
    category = models.CharField(verbose_name=_("category"), max_length=50, choices=Category.choices)
    language = models.CharField(verbose_name=_("language"), max_length=10, default="en", choices=settings.LANGUAGES)
    phone = models.CharField(
        verbose_name=_("phone"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Phone number with country code (eg. +32 490 12 34 56)"),
    )
    email = models.EmailField(verbose_name=_("email"), max_length=255, blank=True, default="")
    website = models.URLField(verbose_name=_("website"), max_length=255, blank=True, default="")
    vat_number = models.CharField(
        verbose_name=_("VAT number"), max_length=255, blank=True, default="", help_text=_("VAT number")
    )
    bank_account_number = models.CharField(
        verbose_name=_("bank account number"), max_length=255, blank=True, default=""
    )

    def __str__(self):
        """Return the string representation of the relation."""
        return self.name

    def get_vat_number_display(self):
        """Return the VAT number for display."""
        vat_str = _("VAT")
        return f"{vat_str} {self.vat_number}"

    class Meta:
        """Set meta options."""

        verbose_name = _("relation")
        verbose_name_plural = _("relations")
