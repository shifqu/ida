"""Companies admin."""

from django.contrib import admin

from apps.companies.models import BankAccount, Company
from apps.geo.admin import AddressInline


class BankAccountInline(admin.TabularInline):
    """Represent the Bank Account inline to add/remove bank accounts."""

    model = BankAccount
    extra = 0


class CompanyAdmin(admin.ModelAdmin):
    """Represent the Company admin."""

    inlines = [AddressInline, BankAccountInline]


admin.site.register(Company, CompanyAdmin)
