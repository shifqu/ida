"""Django command to create an invoice for a project for a given month/year."""

import calendar

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import override

from apps.invoices.models import Invoice, InvoiceItem
from apps.projects.models import Project, Rate
from apps.timesheets.models import Timesheet


class Command(BaseCommand):
    """Create an invoice."""

    help = "Create an invoice for a project for a given month/year (optionally for a specific user)"

    def add_arguments(self, parser):
        """Add command line arguments."""
        now = timezone.now()
        parser.add_argument("project_id", type=int, help="ID of the project")
        parser.add_argument("--month", type=int, default=now.month, help="Month (1-12)")
        parser.add_argument("--year", type=int, default=now.year, help="Year (e.g. 2025)")

    def handle(self, *_args, **options):
        """Create an invoice for the specified project, month, and year."""
        project_id = options["project_id"]
        month = options["month"]
        year = options["year"]
        return self._create_invoice(project_id, month, year)

    def _create_invoice(self, project_id, month, year):
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist as exc:
            raise CommandError(f"Project with id {project_id} does not exist.") from exc

        zfilled_month = str(month).zfill(2)
        timesheets = Timesheet.objects.filter(
            project=project, month=month, year=year, status=Timesheet.Status.COMPLETED, user__is_active=True
        )
        if not timesheets.exists():
            self.stdout.write(
                self.style.WARNING(f"No completed timesheets found for project {project} in {zfilled_month}/{year}.")
            )
            return

        with override(project.relation.language, deactivate=True):
            for timesheet in timesheets:
                last_day = calendar.monthrange(timesheet.year, timesheet.month)[1]
                invoice_date = timezone.datetime(timesheet.year, timesheet.month, last_day).date()
                invoice = Invoice.objects.create(relation=project.relation, company=project.company, date=invoice_date)

                items = self._generate_invoice_items(project, timesheet, invoice)
                if not items:
                    self.stdout.write(
                        self.style.WARNING(f"No invoice items created for project {project} in {zfilled_month}/{year}.")
                    )
                    continue

                invoice.invoiceitem_set.bulk_create(items)

                self.stdout.write(self.style.SUCCESS(f"Created invoice for project {project} with {timesheet}."))

    def _generate_invoice_items(self, project: Project, timesheet: Timesheet, invoice: Invoice) -> list[InvoiceItem]:
        """Generate invoice items based on the project's rates and the timesheet."""
        items = []
        for project_rate in project.rate_set.all():
            total_hours = timesheet.timesheetitem_set.filter(item_type=project_rate.item_type).aggregate(
                total=Sum("worked_hours")
            )["total"]
            if not total_hours:
                continue

            total = self._convert_hours_to_total(project_rate, total_hours)
            if not total:
                self.stdout.write(self.style.ERROR(f"No hours to invoice for {project_rate} on project {project}."))
                continue

            item_description = (
                f"[{project.invoice_line_prefix}] {project_rate.get_item_type_display()} "
                f"({project_rate.get_rate_type_display()})"
            )
            item = InvoiceItem(
                invoice=invoice,
                description=item_description,
                unit_price=project_rate.rate,
                quantity=total,
                vat_percentage=project_rate.vat_percentage,
            )
            items.append(item)
        return items

    def _convert_hours_to_total(self, project_rate: Rate, total_hours: float) -> float:
        """Convert total hours to the total amount based on the rate type."""
        match project_rate.rate_type:
            case project_rate.RateType.HOURLY:
                total = total_hours
            case project_rate.RateType.DAILY:
                total = total_hours / 8
            case project_rate.RateType.MONTHLY:
                total = 1.0
            case _:
                total = 0.0

        return total
