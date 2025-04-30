"""Users models."""

from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class IdaUser(AbstractUser):
    """Extend the default user model."""

    if TYPE_CHECKING:
        from apps.companies.models import Company
        from apps.telegram.models import TelegramSettings

        company: models.ForeignKey[Company | None]
        telegramsettings: models.OneToOneField[TelegramSettings | None]

    company = models.ForeignKey(
        "companies.Company", on_delete=models.SET_NULL, verbose_name=_("company"), null=True, blank=True
    )
    language = models.CharField(verbose_name=_("language"), max_length=10, default="en", choices=settings.LANGUAGES)

    def __str__(self):
        """Return a string representation of the user setting."""
        super_ = super().__str__()
        return f"{super_} ({self.language})"
