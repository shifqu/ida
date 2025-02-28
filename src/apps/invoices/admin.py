"""Invoices admin."""

from django.contrib import admin
from django.db.models import QuerySet

from apps.invoices.models import Invoice, InvoiceItem


@admin.action(description="Create a PDF for the selected invoices")
def create_pdf(modeladmin, request, queryset: QuerySet[Invoice]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Create a PDF for the selected invoices."""
    for invoice in queryset:
        invoice.create_pdf()


class InvoiceItemInline(admin.TabularInline):
    """Represent the InvoiceItem inline to add/remove items in the invoice admin."""

    model = InvoiceItem
    extra = 0


class InvoiceAdmin(admin.ModelAdmin):
    """Represent the Invoice admin."""

    inlines = [InvoiceItemInline]
    list_display = ("number", "date", "relation", "total")
    readonly_fields = ("number", "date_due", "payment_communication", "subtotal", "vat_amount", "total")
    actions = [create_pdf]


admin.site.register(Invoice, InvoiceAdmin)
