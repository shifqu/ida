"""Django settings for ida project.

Generated by 'django-admin startproject' using Django 5.1.6.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

import json
from pathlib import Path

from django.utils.translation import gettext_noop

from ida import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = environ.from_env("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = environ.from_env("DJANGO_DEBUG", True, astype=environ.strtobool)

ALLOWED_HOSTS = environ.from_env("DJANGO_ALLOWED_HOSTS", [], astype=json.loads)


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.companies",
    "apps.geo",
    "apps.relations",
    "apps.invoices",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ida.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ida.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

# Languages we provide translations for, out of the box.
# Full list of language codes supported by Django can be found here:
# https://docs.djangoproject.com/en/5.1/ref/settings/#languages
LANGUAGES = [
    ("de", gettext_noop("German")),
    ("en", gettext_noop("English")),
    ("fr", gettext_noop("French")),
    ("nl", gettext_noop("Dutch")),
]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "static/"

# Media files (user-uploaded files)
# https://docs.djangoproject.com/en/5.1/topics/files/#managing-files

MEDIA_URL = "media/"
MEDIA_ROOT = environ.from_env("DJANGO_MEDIA_ROOT", default=BASE_DIR / "media", astype=Path)

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email settings
# https://docs.djangoproject.com/en/5.1/topics/email/#module-django.core.mail

EMAIL_BACKEND = environ.from_env("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = environ.from_env("DJANGO_EMAIL_HOST")
EMAIL_PORT = environ.from_env("DJANGO_EMAIL_PORT")
EMAIL_USE_TLS = environ.from_env("DJANGO_EMAIL_USE_TLS", False, astype=environ.strtobool)
EMAIL_HOST_USER = environ.from_env("DJANGO_EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = environ.from_env("DJANGO_EMAIL_HOST_PASSWORD")


# Custom settings

ADMIN = {
    "SITE_HEADER": environ.from_env("ADMIN_SITE_HEADER", "IDA Administration"),
    "ROOT_URL": environ.from_env("ADMIN_ROOT_URL", "admin/"),
}
