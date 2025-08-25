"""Projects admin."""

from django.contrib import admin

from apps.projects.models import Project, Rate


class RateInline(admin.TabularInline):
    """Represent rates inline in the admin."""

    model = Rate
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    """Represent the Project admin."""

    filter_horizontal = ("users",)
    inlines = [RateInline]


admin.site.register(Project, ProjectAdmin)
