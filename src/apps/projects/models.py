"""Projects models."""

import decimal
from typing import TYPE_CHECKING, Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.timesheets.models import TimesheetItem


class Project(models.Model):
    """Represent a project."""

    if TYPE_CHECKING:
        from apps.companies.models import Company
        from apps.relations.models import Relation
        from apps.users.models import IdaUser

        company: models.ForeignKey[Company]
        rate_set: models.Manager["Rate"]
        relation: models.ForeignKey[Relation]
        users: models.ManyToManyField[IdaUser, Any]

    name = models.CharField(verbose_name=_("name"), max_length=255, unique=True)
    description = models.TextField(verbose_name=_("description"), blank=True)
    start_date = models.DateField(verbose_name=_("start date"))
    end_date = models.DateField(verbose_name=_("end date"))
    users = models.ManyToManyField("users.IdaUser", related_name="projects", blank=True, verbose_name=_("users"))
    relation = models.ForeignKey("relations.Relation", on_delete=models.CASCADE, verbose_name=_("relation"))
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        verbose_name=_("company"),
        help_text=_("The company that executes work for this project"),
    )
    invoice_line_prefix = models.CharField(
        verbose_name=_("invoice line prefix"), max_length=50, help_text=_("Prefix for invoice lines, e.g. 'IT-Service'")
    )

    def __str__(self):
        """Return a string representation of the project."""
        return self.name

    class Meta:
        """Set meta options."""

        verbose_name = _("project")
        verbose_name_plural = _("projects")


class Rate(models.Model):
    """Represent a rate for a project."""

    if TYPE_CHECKING:

        def get_item_type_display(self) -> str: ...  # noqa: D102
        def get_rate_type_display(self) -> str: ...  # noqa: D102

    class RateType(models.IntegerChoices):
        """Define the rate types."""

        DAILY = 1, _("Daily")
        HOURLY = 2, _("Hourly")
        MONTHLY = 3, _("Monthly")

    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("project"))
    item_type = models.IntegerField(verbose_name=_("item type"), choices=TimesheetItem.ItemType.choices)
    rate_type = models.IntegerField(verbose_name=_("rate type"), choices=RateType.choices, default=RateType.HOURLY)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    vat_percentage = models.DecimalField(
        verbose_name=_("VAT"),
        default=decimal.Decimal(21),
        max_digits=5,
        decimal_places=2,
        help_text=_("VAT percentage"),
    )

    class Meta:
        """Set meta options."""

        unique_together = ("project", "item_type")
        verbose_name = _("project rate")
        verbose_name_plural = _("project rates")

    def __str__(self):
        """Return a string representation of the rate."""
        item_type = self.get_item_type_display()
        rate_type = self.get_rate_type_display()
        return f"{self.project.name} - {item_type}: {self.rate} x {self.vat_percentage}% ({rate_type})"
