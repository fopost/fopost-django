from __future__ import annotations

from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from fopost import DEFAULT_BASE_URL

from fopost_django import get_settings
from fopost_django.apps import FopostConfig


def test_missing_api_key_raises(settings: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FOPOST_API_KEY", raising=False)
    settings.FOPOST = {}

    with pytest.raises(ImproperlyConfigured, match="API_KEY"):
        get_settings()


def test_app_config_ready_raises_without_a_key(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FOPOST_API_KEY", raising=False)
    settings.FOPOST = {}

    import fopost_django

    config = FopostConfig("fopost_django", fopost_django)
    with pytest.raises(ImproperlyConfigured, match="API_KEY"):
        config.ready()


def test_api_key_falls_back_to_the_environment(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FOPOST_API_KEY", "fp_from_env")
    settings.FOPOST = {}

    assert get_settings().api_key == "fp_from_env"


def test_settings_dict_wins_over_the_environment(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FOPOST_API_KEY", "fp_from_env")
    settings.FOPOST = {"API_KEY": "fp_from_settings"}

    assert get_settings().api_key == "fp_from_settings"


def test_defaults_fill_in_the_rest(settings: Any) -> None:
    settings.FOPOST = {"API_KEY": "fp_x"}
    resolved = get_settings()

    # The default is whatever the parent SDK ships, not a literal restated here;
    # the prefix itself is the SDK's own test to make.
    assert resolved.base_url == DEFAULT_BASE_URL
    assert resolved.timeout == 30.0
    assert resolved.max_retries == 3
    assert resolved.webhook_secret is None


def test_unknown_key_is_a_typo_not_a_feature(settings: Any) -> None:
    settings.FOPOST = {"API_KEY": "fp_x", "APIKEY": "oops"}

    with pytest.raises(ImproperlyConfigured, match="APIKEY"):
        get_settings()


@pytest.mark.parametrize(
    "overrides",
    [
        {"TIMEOUT": 0},
        {"TIMEOUT": "soon"},
        {"MAX_RETRIES": 0},
        {"BASE_URL": ""},
        {"DEFAULT_WORKSPACE_ID": 42},
    ],
)
def test_bad_values_are_rejected(settings: Any, overrides: dict[str, Any]) -> None:
    settings.FOPOST = {"API_KEY": "fp_x", **overrides}

    with pytest.raises(ImproperlyConfigured):
        get_settings()
