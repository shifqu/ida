"""URL configuration for telegram app."""

from django.conf import settings
from django.urls import path

from apps.telegram import views

urlpatterns = [
    path(settings.TELEGRAM["WEBHOOK_URL"], views.webhook, name="webhook"),
]
