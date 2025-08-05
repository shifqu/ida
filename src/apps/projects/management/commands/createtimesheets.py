"""Django command to create timesheets for active projects."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.projects.models import Project
from apps.timesheets.models import Timesheet


class Command(BaseCommand):
    """Create a timesheet."""

    help = "Create a timesheet for all active projects."

    def add_arguments(self, parser):
        """Add command line arguments."""
        now = timezone.now()
        parser.add_argument("--month", type=int, default=now.month, help=f"Month (1-12), default {now.month}")
        parser.add_argument("--year", type=int, default=now.year, help=f"Year (e.g. 2025), default {now.year}")
        parser.add_argument(
            "--project_id", type=int, default=0, help="ID of the project, if not provided, all projects will be used."
        )
        parser.add_argument(
            "--user_id", type=int, default=0, help="ID of the user, if not provided, all users will be used."
        )

    def handle(self, *_args, **options):
        """Create a timesheet for the specified project, month, and year."""
        project_id = options["project_id"]
        month = options["month"]
        year = options["year"]
        user_id = options["user_id"]
        return self._create_timesheets(project_id, month, year, user_id)

    def _create_timesheets(self, project_id: int, month: int, year: int, user_id: int):
        projects = self._get_projects(project_id)
        zfilled_month = str(month).zfill(2)
        for project in projects:
            if not user_id:
                user_ids = project.users.values_list("id", flat=True)
            else:
                user_ids = [user_id]
            for user_id in user_ids:
                timesheet, created = Timesheet.objects.get_or_create(
                    project=project,
                    month=month,
                    year=year,
                    user_id=user_id,
                )
                action = "created" if created else "already exists"
                msg = f"Timesheet {action} for user {timesheet.user} on project {project} in {zfilled_month}/{year}."
                if not created:
                    self.stdout.write(self.style.WARNING(msg))
                else:
                    self.stdout.write(self.style.SUCCESS(msg))

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
