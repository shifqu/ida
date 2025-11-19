"""Base telegram settings."""

from abc import ABC

from django_telegram_app.bot.base import BaseCommand, Step

from apps.telegram.models import TelegramSettings


class TelegramCommand(BaseCommand, ABC):
    """Project specific base class for telegram commands."""

    settings: TelegramSettings


class TelegramStep(Step, ABC):
    """Project specific base class for telegram command steps."""

    command: TelegramCommand
