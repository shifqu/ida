"""URL configuration for telegram app."""

from django.urls import path

from apps.telegram import views
from apps.telegram.conf import settings

urlpatterns = [
    path(settings.WEBHOOK_URL, views.webhook, name="webhook"),
]
