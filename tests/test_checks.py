from __future__ import annotations

from typing import Any

from fopost_django.checks import (
    API_KEY_IN_SETTINGS_ID,
    INSECURE_BASE_URL_ID,
    WEBHOOK_SECRET_ID,
    check_fopost_settings,
)


def ids(settings: Any) -> set[str]:
    return {message.id for message in check_fopost_settings()}


def test_a_wired_webhook_with_no_secret_warns(settings: Any) -> None:
    settings.FOPOST = {**settings.FOPOST, "WEBHOOK_SECRET": None}

    assert WEBHOOK_SECRET_ID in ids(settings)


def test_a_configured_secret_is_quiet(settings: Any) -> None:
    assert WEBHOOK_SECRET_ID not in ids(settings)


def test_a_plaintext_base_url_warns(settings: Any) -> None:
    settings.FOPOST = {**settings.FOPOST, "BASE_URL": "http://api.example.com/api/v1"}

    assert INSECURE_BASE_URL_ID in ids(settings)


def test_localhost_over_http_is_fine(settings: Any) -> None:
    settings.FOPOST = {**settings.FOPOST, "BASE_URL": "http://localhost:8080/api/v1"}

    assert INSECURE_BASE_URL_ID not in ids(settings)


def test_a_hardcoded_key_warns(settings: Any) -> None:
    assert API_KEY_IN_SETTINGS_ID in ids(settings)
