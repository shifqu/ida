"""Timesheets admin."""

from django import forms
from django.contrib import admin
from django.db import models
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy as _

from apps.timesheets.models import Timesheet, TimesheetItem


@admin.action(permissions=["change"], description=_("Mark the selected timesheets as completed"))
def mark_timesheets_as_completed(modeladmin, request, queryset: QuerySet[Timesheet]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Mark the selected timesheets as completed."""
    for timesheet in queryset:
        timesheet.mark_as_completed()


class TimesheetItemInline(admin.TabularInline):
    """Represent the TimesheetItem inline to add/remove items in the timesheet admin."""

    model = TimesheetItem
    extra = 0
    ordering = ["date"]

    formfield_overrides = {models.TextField: {"widget": forms.Textarea(attrs={"cols": 40})}}


class TimesheetAdmin(admin.ModelAdmin):
    """Represent the Timesheet admin."""

    inlines = [TimesheetItemInline]
    actions = [mark_timesheets_as_completed]


admin.site.register(Timesheet, TimesheetAdmin)
