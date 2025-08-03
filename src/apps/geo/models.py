"""Geo models."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Address(models.Model):
    """Represent an address."""

    class Country(models.TextChoices):
        """Represent the country choices."""

        BELGIUM = "BE", _("Belgium")
        NETHERLANDS = "NL", _("Netherlands")
        UNITED_KINGDOM = "UK", _("United Kingdom")

    line1 = models.CharField(verbose_name=_("line1"), max_length=255, help_text=_("Example: dummystreet 42a"))
    line2 = models.CharField(verbose_name=_("line2"), max_length=255, blank=True, default="")
    line3 = models.CharField(verbose_name=_("line3"), max_length=255, blank=True, default="")
    line4 = models.CharField(verbose_name=_("line4"), max_length=255, blank=True, default="")
    postal_code = models.CharField(verbose_name=_("postal code"), max_length=20)
    city = models.CharField(verbose_name=_("city"), max_length=100)
    state_province_region = models.CharField(
        verbose_name=_("state province region"), max_length=100, blank=True, default=""
    )
    country = models.CharField(
        verbose_name=_("country"), max_length=10, choices=Country.choices, default=Country.BELGIUM
    )
    relation = models.ForeignKey(
        "relations.Relation", on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("relation")
    )
    company = models.ForeignKey(
        "companies.Company", on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("company")
    )

    def __str__(self):
        """Return the address as a string.

        `None` is passed to `filter` in order to remove false values (None, "", ...) from the
        list of address components.
        """
        filtered_fields = filter(
            None,
            [
                self.line1,
                self.line2,
                self.line3,
                self.line4,
                f"{self.postal_code} {self.city}",
                self.state_province_region,
                self.get_country_display(),  # type: ignore[reportAttributeAccessIssue]
            ],
        )
        return "\n".join(filtered_fields)

    class Meta:
        """Add a correct plural name and a constraint to ensure either a Relation or Company is linked."""

        verbose_name = _("address")
        verbose_name_plural = _("addresses")
        constraints = [
            models.CheckConstraint(
                condition=(  # type: ignore[reportCallIssue]
                    (models.Q(relation__isnull=False) & models.Q(company__isnull=True))
                    | (models.Q(relation__isnull=True) & models.Q(company__isnull=False))
                ),
                name="address_must_have_exactly_one_relation_or_company",
            )
        ]
