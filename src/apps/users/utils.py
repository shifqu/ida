"""Utils for users app."""

from importlib import import_module

from django.apps import apps
from django.contrib.admin.options import InlineModelAdmin


def get_inlines(extra: dict[str, str] | None = None) -> list[type[InlineModelAdmin]]:
    """Dynamically collect user-related inlines from custom apps.

    A custom app is defined as an app that starts with "apps.".
    This function imports the admin module of each custom app and
    collects the inlines defined in it. The inlines are expected to
    be defined in a variable named `user_inlines` within the admin module.

    Extra inlines can be provided via the `extra` parameter, which
    should be a dictionary mapping module names to inline class names.

    ModuleNotFoundError and AttributeError are caught and ignored.
    """
    inlines = []
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith("apps."):
            continue  # skip non custom apps

        try:
            admin_module = import_module(f"{app_config.name}.admin")
            user_inlines = admin_module.user_inlines
        except (ModuleNotFoundError, AttributeError):
            continue
        else:
            inlines.extend(user_inlines)

    extra = extra or {}
    for module_name, inline_name in extra.items():
        try:
            admin_module = import_module(module_name)
            user_inline = getattr(admin_module, inline_name)
        except (ModuleNotFoundError, AttributeError):
            continue
        else:
            inlines.append(user_inline)

    return inlines
