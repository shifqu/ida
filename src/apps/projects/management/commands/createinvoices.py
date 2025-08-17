"""Django command to create invoices for completed timesheets for a given month/year."""

import calendar
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum
from django.db.models.manager import BaseManager
from django.utils import timezone
from django.utils.translation import override

from apps.invoices.models import Invoice, InvoiceItem
from apps.projects.models import Project, Rate
from apps.timesheets.models import Timesheet


class Command(BaseCommand):
    """Create an invoice."""

    help = (
        "Create an invoice for all projects for a given month/year for all users. If no month/year is provided, it "
        "defaults to the previous month."
    )

    def add_arguments(self, parser):
        """Add command line arguments."""
        now = timezone.now()
        default_month, default_year = self._previous(now.month, now.year)
        parser.add_argument("--month", type=int, default=default_month, help=f"Month (1-12), default {default_month}")
        parser.add_argument("--year", type=int, default=default_year, help=f"Year (e.g. 2025), default {default_year}")
        parser.add_argument(
            "--project_id", type=int, default=0, help="ID of the project, if not provided, all projects will be used."
        )
        parser.add_argument(
            "--user_id", type=int, default=0, help="ID of the user, if not provided, all users will be used."
        )

    def handle(self, *_args, **options):
        """Create an invoice for the specified project, month, and year."""
        project_id = options["project_id"]
        month = options["month"]
        year = options["year"]
        user_id = options["user_id"]
        return self._create_invoices(project_id, month, year, user_id)

    def _create_invoices(self, project_id: int, month: int, year: int, user_id: int):
        projects = self._get_projects(project_id)
        zfilled_month = str(month).zfill(2)
        for project in projects:
            timesheets = self._get_timesheets(month, year, user_id, project)
            if not timesheets.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"No completed timesheets found for {user_id=} on project {project=} in {zfilled_month}/{year}."
                    )
                )
                return

            with override(project.relation.language, deactivate=True):
                self._create_invoices_from_timesheets(year, zfilled_month, project, timesheets)

    def _create_invoices_from_timesheets(
        self, year: int, zfilled_month: str, project: Project, timesheets: BaseManager[Timesheet]
    ):
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

            self.stdout.write(self.style.SUCCESS(f"Created invoice for {timesheet}."))

    def _get_timesheets(self, month: int, year: int, user_id: int, project: Project):
        timesheets = Timesheet.objects.filter(
            project=project, month=month, year=year, status=Timesheet.Status.COMPLETED, user__is_active=True
        )
        if user_id:
            timesheets = timesheets.filter(user_id=user_id)
        return timesheets

    def _get_projects(self, project_id: int):
        if project_id:
            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist as exc:
                raise CommandError(f"Project with id {project_id} does not exist.") from exc
            projects = [project]
        else:
            projects = Project.objects.all()
        return projects

    def _generate_invoice_items(self, project: Project, timesheet: Timesheet, invoice: Invoice):
        """Generate invoice items based on the project's rates and the timesheet."""
        items: list[InvoiceItem] = []
        for project_rate in project.rate_set.all():
            total_hours = timesheet.timesheetitem_set.filter(item_type=project_rate.item_type).aggregate(
                total=Sum("worked_hours")
            )["total"]
            if not total_hours:
                continue

            total = self._convert_hours_to_total(project_rate, total_hours)
            if not total:
                self.stdout.write(self.style.NOTICE(f"No hours to invoice for {project_rate} on project {project}."))
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

    def _convert_hours_to_total(self, project_rate: Rate, total_hours: float):
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

    def _previous(self, month: int, year: int):
        """Calculate the previous month and year."""
        if month == 1:
            return datetime.max.month, year - 1
        return month - 1, year
