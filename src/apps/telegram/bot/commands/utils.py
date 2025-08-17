"""Utility functions for Telegram bot commands."""

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.telegram.bot.commands.base import Command


def get_command_cls(name: str) -> type["Command"]:
    """Get the command class based on the name."""
    from apps.telegram.bot.commands.registerovertime import RegisterOvertime
    from apps.telegram.bot.commands.registerwork import RegisterWork

    command_map = {"/registerovertime": RegisterOvertime, "/registerwork": RegisterWork}
    return command_map[name]


def generate_correlation_key():
    """Generate a unique correlation key."""
    return str(uuid.uuid4())
