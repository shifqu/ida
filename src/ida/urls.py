"""URL configuration for ida project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from django.utils.translation import gettext as _
from django_telegram_app.conf import settings as app_settings

admin.site.site_header = _(settings.ADMIN["SITE_HEADER"])

urlpatterns = [
    path(settings.ADMIN["ROOT_URL"], admin.site.urls),
    path(app_settings.ROOT_URL, include("django_telegram_app.urls")),
    path("favicon.ico", lambda _: redirect(f"{settings.STATIC_URL}icons/favicon.ico", permanent=True)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
