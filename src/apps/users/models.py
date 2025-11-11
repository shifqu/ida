"""Users models."""

from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class IdaUser(AbstractUser):
    """Extend the default user model."""

    if TYPE_CHECKING:
        from django_telegram_app.models import TelegramSettings

        from apps.companies.models import Company
        from apps.projects.models import Project

        company: models.ForeignKey[Company | None]
        telegramsettings: models.OneToOneField[TelegramSettings | None]
        projects: models.QuerySet[Project]

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        verbose_name=_("company"),
        null=True,
        blank=True,
        related_name="user_set",
    )
    language = models.CharField(verbose_name=_("language"), max_length=10, default="en", choices=settings.LANGUAGES)

    def __str__(self):
        """Return a string representation of the custom user."""
        super_ = super().__str__()
        return f"{super_} ({self.language})"
