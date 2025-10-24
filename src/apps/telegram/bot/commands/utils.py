"""Utility functions for Telegram bot commands."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.telegram.bot.commands.core import Command


def get_command_list() -> list[type["Command"]]:
    """Return the list of available command classes."""
    from apps.telegram.bot.commands.completetimesheet import CompleteTimesheet
    from apps.telegram.bot.commands.editwork import EditWork
    from apps.telegram.bot.commands.registerovertime import RegisterOvertime
    from apps.telegram.bot.commands.registerwork import RegisterWork
    from apps.telegram.bot.commands.requestoverview import RequestOverview

    return [
        RegisterWork,
        RegisterOvertime,
        CompleteTimesheet,
        EditWork,
        RequestOverview,
    ]


def get_command_cls(name: str):
    """Return the command class based on the name."""
    command_map = {cmd.command: cmd for cmd in get_command_list()}
    return command_map[name]


def prettyprint(data: dict):
    """Pretty print the provided dictionary."""
    return "\n".join([f"{k}={v}" for k, v in data.items()])
