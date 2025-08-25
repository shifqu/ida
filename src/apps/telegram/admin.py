"""Telegram admin."""

from django.contrib import admin

from apps.telegram.models import CallbackData, Message, TelegramSettings, TimeRangeItemTypeRule, WeekdayItemTypeRule


class TelegramSettingInline(admin.TabularInline):
    """Represent a telegram setting inline in the admin."""

    model = TelegramSettings


user_inlines = [TelegramSettingInline]


class CallbackDataAdmin(admin.ModelAdmin):
    """Represent the CallbackData admin."""

    list_display = ("token", "data_truncated")

    def has_add_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to add callback_data."""
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to delete callback_data."""
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to change callback_data."""
        return False


class MessageAdmin(admin.ModelAdmin):
    """Represent the Message admin."""

    list_display = ("update_id", "message_truncated", "error")

    def has_add_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to add messages."""
        return False

    def has_delete_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to delete messages."""
        return False

    def has_change_permission(self, request, obj=None):  # noqa: ARG002  # pylint: disable=unused-argument
        """Do not allow to change messages."""
        return False


class WeekdayItemTypeRuleAdmin(admin.ModelAdmin):
    """Represent the WeekdayItemTypeRule admin."""


class TimeRangeItemTypeRuleAdmin(admin.ModelAdmin):
    """Represent the TimeRangeItemTypeRule admin."""


admin.site.register(CallbackData, CallbackDataAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(WeekdayItemTypeRule, WeekdayItemTypeRuleAdmin)
admin.site.register(TimeRangeItemTypeRule, TimeRangeItemTypeRuleAdmin)
