"""Timesheets models."""

import calendar
from datetime import date
from typing import TYPE_CHECKING

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def current_year():
    """Return the current year."""
    return timezone.now().year


def current_month():
    """Return the current month."""
    return timezone.now().month


class Timesheet(models.Model):
    """Represent a Timesheet."""

    if TYPE_CHECKING:
        from apps.projects.models import Project
        from apps.users.models import IdaUser

        timesheetitem_set: models.Manager["TimesheetItem"]
        user: models.ForeignKey[IdaUser]
        project: models.ForeignKey[Project]

    class Status(models.TextChoices):
        """Represent the status of a timesheet."""

        DRAFT = "draft", _("Draft")
        COMPLETED = "completed", _("Completed")

    month = models.IntegerField(_("month"), default=current_month)
    year = models.IntegerField(_("year"), default=current_year)
    status = models.CharField(_("status"), max_length=50, choices=Status.choices, default=Status.DRAFT)
    user = models.ForeignKey("users.IdaUser", on_delete=models.CASCADE, verbose_name=_("user"))
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, verbose_name=_("project"))

    class Meta:
        """Set meta options."""

        unique_together = ("user", "project", "month", "year")

    @property
    def name(self) -> str:
        """Return the name of the timesheet."""
        user_name = self.user.first_name
        if self.user.last_name:
            user_name = f"{user_name} {self.user.last_name}"
        return f"{self.project} - {user_name} - {str(self.month).zfill(2)}/{self.year}"

    def get_missing_days(self) -> list[date]:
        """Return the dates for the standard days missing in the timesheet."""
        if self.status == self.Status.COMPLETED:
            return []

        nb_of_days = self._get_number_of_days()

        days = range(1, nb_of_days + 1)
        existing_days = self.timesheetitem_set.filter(item_type=TimesheetItem.ItemType.STANDARD).values_list(
            "date__day", flat=True
        )

        return self._get_missing_dates(days, existing_days)

    def _get_missing_dates(self, days, existing_days):
        dates: list[date] = []
        for day in days:
            if day in existing_days:
                continue
            date_ = date(year=self.year, month=self.month, day=day)
            if date_.weekday() >= 5:
                continue
            dates.append(date_)
        return dates

    def _get_number_of_days(self):
        now = timezone.now()
        if self.month == now.month and self.year == now.year:
            nb_of_days = now.day
        else:
            nb_of_days = calendar.monthrange(self.year, self.month)[1]
        return nb_of_days

    def __str__(self):
        """Return the string representation of the timesheet."""
        return self.name


class TimesheetItem(models.Model):
    """Represent a Timesheet."""

    class ItemType(models.TextChoices):
        """Represent the type of timesheet item."""

        STANDARD = "standard", _("Standard")
        ON_CALL = "on_call", _("On call")
        NIGHT = "night", _("Night")
        SATURDAY = "saturday", _("Saturday")
        SUNDAY = "sunday", _("Sunday")
        OTHER = "other", _("Other")

    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, verbose_name=_("timesheet"))
    item_type = models.CharField(
        verbose_name=_("item type"), max_length=50, choices=ItemType.choices, default=ItemType.STANDARD
    )
    date = models.DateField(verbose_name=_("date"))
    worked_hours = models.FloatField(verbose_name=_("worked hours"))
    description = models.TextField(verbose_name=_("description"), blank=True)

    def __str__(self):
        """Return the string representation of the timesheet item."""
        return f"{self.date} - {self.worked_hours} hours ({self.description})"
