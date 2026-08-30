"""Minimal project settings for the test suite."""

SECRET_KEY = "fopost-django-tests"
DEBUG = False
ALLOWED_HOSTS = ["*"]
USE_TZ = True

INSTALLED_APPS = ["fopost_django"]

DATABASES: dict[str, dict[str, str]] = {}

ROOT_URLCONF = "tests.urls"

MIDDLEWARE: list[str] = []

TEMPLATES: list[dict[str, object]] = []

FOPOST = {
    "API_KEY": "fp_test_key",
    "BASE_URL": "https://api.test.fopost.com/api/v1",
    "WEBHOOK_SECRET": "whsec_test",
    "DEFAULT_WORKSPACE_ID": "ws_default",
}

LOGGING_CONFIG = None
