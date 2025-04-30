"""Users admin."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.users.models import IdaUser
from apps.users.utils import get_inlines


class IdaUserAdmin(UserAdmin):
    """Add the UserSetting to the User admin interface."""

    model = IdaUser
    fieldsets = UserAdmin.fieldsets + ((_("Ida data"), {"fields": ("language", "company")}),)  # type: ignore[reportOperatorIssue]
    add_fieldsets = UserAdmin.add_fieldsets + ((_("Ida data"), {"fields": ("language", "company")}),)
    inlines = get_inlines()


admin.site.register(IdaUser, IdaUserAdmin)
