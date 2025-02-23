"""Companies admin."""

from django.contrib import admin

from apps.companies.models import Company
from apps.geo.admin import AddressInline


class CompanyAdmin(admin.ModelAdmin):
    """Represent the Company admin."""

    inlines = [AddressInline]


admin.site.register(Company, CompanyAdmin)
