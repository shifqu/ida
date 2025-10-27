"""Bot commands for the Telegram app."""

from apps.telegram.bot.commands._core import Command, get_command_cls, get_command_list

__all__ = ["Command", "get_command_cls", "get_command_list"]
