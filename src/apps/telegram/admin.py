"""Telegram admin."""

from django.contrib import admin

from apps.telegram.models import Message, TelegramSettings


class TelegramSettingInline(admin.TabularInline):
    """Represent a telegram setting inline in the admin."""

    model = TelegramSettings


user_inlines = [TelegramSettingInline]


class MessageAdmin(admin.ModelAdmin):
    """Represent the Message admin."""

    def has_add_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to add messages."""
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to delete messages."""
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to change messages."""
        return False


admin.site.register(Message, MessageAdmin)
