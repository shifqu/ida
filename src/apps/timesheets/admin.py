"""Timesheets admin."""

from django.contrib import admin

from apps.timesheets.models import Timesheet, TimesheetItem

# @admin.action(description="Create a PDF for the selected timesheets")
# def create_pdf(modeladmin, request, queryset: QuerySet[Timesheet]):  # noqa: ARG001  # pylint: disable=unused-argument
#     """Create a PDF for the selected timesheets."""
#     for timesheet in queryset:
#         timesheet.create_pdf()


class TimesheetItemInline(admin.TabularInline):
    """Represent the TimesheetItem inline to add/remove items in the timesheet admin."""

    model = TimesheetItem
    extra = 0


class TimesheetAdmin(admin.ModelAdmin):
    """Represent the Timesheet admin."""

    inlines = [TimesheetItemInline]
    # list_display = ("number", "date", "relation", "total")
    # readonly_fields = ("number", "date_due", "payment_communication", "subtotal", "vat_amount", "total")
    # actions = [create_pdf]

    # def has_delete_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
    #     """Do not allow to delete timesheets."""
    #     return False


admin.site.register(Timesheet, TimesheetAdmin)
