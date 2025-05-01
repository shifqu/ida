"""Invoices admin."""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from apps.invoices.models import Invoice, InvoiceItem


@admin.action(permissions=["change"], description="Confirm the selected invoices")
def confirm_pdf(modeladmin, request, queryset: QuerySet[Invoice]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Confirm the selected invoices."""
    for invoice in queryset:
        try:
            invoice.confirm()
        except ValidationError as error:
            messages.error(request, f"{invoice}: {error}")


@admin.action(permissions=["change"], description="Mark the selected invoices as paid")
def mark_as_paid(modeladmin, request, queryset: QuerySet[Invoice]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Mark the selected invoices as paid."""
    for invoice in queryset:
        try:
            invoice.mark_as_paid()
        except ValidationError as error:
            messages.error(request, f"{invoice}: {error}")


@admin.action(permissions=["change"], description="Create a PDF for the selected invoices")
def create_pdf(modeladmin, request, queryset: QuerySet[Invoice]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Create a PDF for the selected invoices."""
    for invoice in queryset:
        try:
            invoice.create_pdf()
        except ValidationError as error:
            messages.error(request, f"{invoice}: {error}")


@admin.action(permissions=["change"], description="Send the selected invoices by email")
def send_by_email(modeladmin, request, queryset: QuerySet[Invoice]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Send the selected invoices by email.

    If an invoice does not have a pdf, it will be created.
    If the invoice was already sent, it will NOT be sent again.
    """
    for invoice in queryset:
        try:
            invoice.send_by_email()
        except ValidationError as error:
            messages.error(request, f"{invoice}: {error}")


@admin.action(permissions=["change"], description="Send the selected invoices by email (even if already sent)")
def send_by_email_allow_resend(modeladmin, request, queryset: QuerySet[Invoice]):  # noqa: ARG001  # pylint: disable=unused-argument
    """Send the selected invoices by email.

    If an invoice does not have a pdf, it will be created.
    If the invoice was already sent, it will be sent again.
    """
    for invoice in queryset:
        try:
            invoice.send_by_email(even_if_already_sent=True)
        except ValidationError as error:
            messages.error(request, f"{invoice}: {error}")


class InvoiceItemInline(admin.TabularInline):
    """Represent the InvoiceItem inline to add/remove items in the invoice admin."""

    model = InvoiceItem
    extra = 0


class InvoiceAdmin(admin.ModelAdmin):
    """Represent the Invoice admin."""

    inlines = [InvoiceItemInline]
    list_display = ("number", "date", "relation", "total", "status")
    list_filter = ("status",)
    search_fields = ("number", "relation__name")
    readonly_fields = ("status", "number", "date_due", "payment_communication", "subtotal", "vat_amount", "total")
    actions = [confirm_pdf, create_pdf, send_by_email, send_by_email_allow_resend]

    def has_delete_permission(self, request, obj: Invoice | None = None):
        """Do not allow to delete invoices that are not new or in draft."""
        if obj is not None and obj.status != Invoice.Status.DRAFT:
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj: Invoice | None = None):
        """Do not allow to change invoices that are not new or in draft."""
        if obj is not None and obj.status != Invoice.Status.DRAFT:
            return False
        return super().has_change_permission(request, obj)


admin.site.register(Invoice, InvoiceAdmin)
