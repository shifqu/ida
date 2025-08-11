"""Utility functions for Telegram bot commands."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.telegram.bot.commands.base import Command


def get_command_cls(name: str) -> type["Command"]:
    """Get the command class based on the name."""
    from apps.telegram.bot.commands.registerovertime import RegisterOvertime
    from apps.telegram.bot.commands.registerwork import RegisterWork

    command_map = {
        # "/registeroncall": RegisterOnCall,
        "/registerovertime": RegisterOvertime,
        "/registerwork": RegisterWork,
    }
    return command_map[name]
