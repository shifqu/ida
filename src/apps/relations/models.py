"""Relations models."""

from django.conf.global_settings import LANGUAGES
from django.db import models
from django.utils.translation import gettext_lazy as _


class Relation(models.Model):
    """Represent a relation."""

    class Category(models.TextChoices):
        """Represent the relation type choices."""

        CUSTOMER = "CUSTOMER", _("Customer")
        SUPPLIER = "SUPPLIER", _("Supplier")

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=Category.choices)
    language = models.CharField(max_length=10, default="en", choices=LANGUAGES)
    phone = models.CharField(
        max_length=255, blank=True, default="", help_text=_("Phone number with country code (eg. +32 490 12 34 56)")
    )
    email = models.EmailField(max_length=255, blank=True, default="")
    website = models.URLField(max_length=255, blank=True, default="")
    vat_number = models.CharField(max_length=255, blank=True, default="")
    bank_account_number = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        """Return the string representation of the relation."""
        return self.name
