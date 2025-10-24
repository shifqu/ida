"""Timesheets models."""

import calendar
from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING

from django.core.validators import MaxValueValidator, MinValueValidator
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

    month = models.IntegerField(
        _("month"), default=current_month, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField(_("year"), default=current_year)
    status = models.CharField(_("status"), max_length=50, choices=Status.choices, default=Status.DRAFT)
    user = models.ForeignKey("users.IdaUser", on_delete=models.CASCADE, verbose_name=_("user"))
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, verbose_name=_("project"))

    def save(self, *args, **kwargs):
        """Override save method to ensure full_clean is called."""
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        """Set meta options."""

        unique_together = ("user", "project", "month", "year")

    @property
    def name(self):
        """Return the name of the timesheet."""
        user_name = self.user.first_name
        if self.user.last_name:
            user_name = f"{user_name} {self.user.last_name}"
        if not user_name:
            user_name = self.user.username
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

    def mark_as_completed(self):
        """Mark the timesheet as completed.

        If the timesheet already has the COMPLETED status, do nothing.
        """
        if self.status == self.Status.COMPLETED:
            return
        self.status = self.Status.COMPLETED
        self.save()

    def get_overview(self, include_details: bool = False) -> str:
        """Return an overview of the timesheet.

        When include_details is True, return a detailed overview including each timesheet item.
        Otherwise, only total hours per item type are returned.

        Example output:
        Detailed Timesheet Overview for Project X - John Doe - 05/2024:
        - 2025-05-02 - Standard - 8.0 hours (example std description)
        - 2025-05-01 - Night - 2.0 hours (example description)
        ...
        Totals for Project X - John Doe - 05/2024:
        - 140 hours (Standard)
        - 20 hours (On call)
        - 2 hours (Night)
        - 1 hour (Saturday)
        - 0 hours (Sunday)
        - 0 hours (Other)
        """
        detail_lines = [f"Detailed Timesheet Overview for {self}:"]
        items = self.timesheetitem_set.all().order_by("item_type", "date")
        total_hours_by_type = defaultdict(float)
        for item in items:
            detail_lines.append(str(item))
            total_hours_by_type[item.get_item_type_display()] += item.worked_hours

        overview_lines = [f"Totals for {self}:"]
        for label, total_hours in total_hours_by_type.items():
            hour_str = "hour" if total_hours == 1 else "hours"
            overview_lines.append(f"- {total_hours} {hour_str} ({label})")

        overview = "\n".join(overview_lines)
        if not include_details:
            return overview

        details = "\n".join(detail_lines)
        return "\n\n".join([details, overview])

    def get_holidays_overview(self) -> str:
        """Return an overview of holidays in the timesheet.

        Example output:
        Holidays Overview for Project X - John Doe - 05/2024:
        - 2025-05-01
        - 2025-05-08
        ...
        """
        holiday_lines = [f"Holidays Overview for {self}:"]
        filter_kwargs = {"item_type": TimesheetItem.ItemType.STANDARD, "worked_hours": 0.0}
        items = self.timesheetitem_set.filter(**filter_kwargs).order_by("date")
        for item in items:
            holiday_lines.append(item.date.isoformat())

        return "\n".join(holiday_lines)


class TimesheetItem(models.Model):
    """Represent a Timesheet."""

    if TYPE_CHECKING:

        def get_item_type_display(self) -> str: ...  # noqa: D102

    class ItemType(models.IntegerChoices):
        """Represent the type of timesheet item."""

        STANDARD = 1, _("Standard")
        ON_CALL = 2, _("On call")
        NIGHT = 3, _("Night")
        SATURDAY = 4, _("Saturday")
        SUNDAY = 5, _("Sunday")
        OTHER = 6, _("Other")

    timesheet = models.ForeignKey(Timesheet, on_delete=models.CASCADE, verbose_name=_("timesheet"))
    item_type = models.IntegerField(verbose_name=_("item type"), choices=ItemType.choices, default=ItemType.STANDARD)
    date = models.DateField(verbose_name=_("date"))
    worked_hours = models.FloatField(verbose_name=_("worked hours"))
    description = models.TextField(verbose_name=_("description"), blank=True)

    def __str__(self):
        """Return the string representation of the timesheet item."""
        timesheet_item = f"{self.date} - {self.get_item_type_display()} - {self.worked_hours} hours"
        if self.description:
            timesheet_item = f"{timesheet_item} ({self.description})"
        return timesheet_item
