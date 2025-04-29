"""Utils for users app."""

from importlib import import_module

from django.apps import apps


def get_inlines():
    """Dynamically collect user-related inlines from custom apps.

    A custom app is defined as an app that starts with "apps.".
    This function imports the admin module of each custom app and
    collects the inlines defined in it. The inlines are expected to
    be defined in a variable named `user_inlines` within the admin module.
    """
    inlines = []
    for app_config in apps.get_app_configs():
        if not app_config.name.startswith("apps."):
            continue  # skip non custom apps

        try:
            admin_module = import_module(f"{app_config.name}.admin")
            user_inlines = admin_module.user_inlines
        except ModuleNotFoundError:
            continue
        except AttributeError:
            continue
        else:
            inlines.extend(user_inlines)

    return inlines
