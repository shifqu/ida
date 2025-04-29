"""Users admin."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.users.utils import get_inlines

User = get_user_model()


class IdaUserAdmin(UserAdmin):
    """Add the UserSetting to the User admin interface."""

    model = User
    fieldsets = UserAdmin.fieldsets + ((_("Ida data"), {"fields": ("language", "company")}),)  # type: ignore[reportOperatorIssue]
    add_fieldsets = UserAdmin.add_fieldsets + ((_("Ida data"), {"fields": ("language", "company")}),)
    inlines = get_inlines()


admin.site.register(User, IdaUserAdmin)
