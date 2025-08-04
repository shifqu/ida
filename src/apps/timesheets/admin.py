"""Timesheets admin."""

from django.contrib import admin

from apps.timesheets.models import Timesheet, TimesheetItem


class TimesheetItemInline(admin.TabularInline):
    """Represent the TimesheetItem inline to add/remove items in the timesheet admin."""

    model = TimesheetItem
    extra = 0


class TimesheetAdmin(admin.ModelAdmin):
    """Represent the Timesheet admin."""

    inlines = [TimesheetItemInline]


admin.site.register(Timesheet, TimesheetAdmin)
