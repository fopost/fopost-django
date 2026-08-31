"""Reading and validating the ``FOPOST`` settings dict.

Everything the wrapper needs lives in one dict in Django settings::

    FOPOST = {
        "API_KEY": os.environ["FOPOST_API_KEY"],
        "WEBHOOK_SECRET": os.environ["FOPOST_WEBHOOK_SECRET"],
    }

Every key is optional except ``API_KEY``, which falls back to the
``FOPOST_API_KEY`` environment variable.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.core.signals import setting_changed
from django.dispatch import receiver
from fopost import DEFAULT_BASE_URL

__all__ = [
    "DEFAULTS",
    "SETTINGS_NAME",
    "FopostSettings",
    "get_settings",
    "reset_settings",
]

#: The Django settings name the whole configuration lives under.
SETTINGS_NAME = "FOPOST"

DEFAULTS: dict[str, Any] = {
    "API_KEY": None,
    "BASE_URL": DEFAULT_BASE_URL,
    "TIMEOUT": 30.0,
    "MAX_RETRIES": 3,
    "DEFAULT_WORKSPACE_ID": None,
    "WEBHOOK_SECRET": None,
    # Advanced: an httpx.Client to send through instead of a fresh one. Handy
    # for a corporate proxy, and for stubbing the transport in tests.
    "HTTP_CLIENT": None,
}

#: Settings that read an environment variable when the dict leaves them out.
ENV_FALLBACKS = {
    "API_KEY": "FOPOST_API_KEY",
    "BASE_URL": "FOPOST_BASE_URL",
    "WEBHOOK_SECRET": "FOPOST_WEBHOOK_SECRET",
    "DEFAULT_WORKSPACE_ID": "FOPOST_WORKSPACE_ID",
}


@dataclass(frozen=True, slots=True)
class FopostSettings:
    """The resolved configuration, with defaults and env fallbacks applied."""

    api_key: str
    base_url: str
    timeout: float
    max_retries: int
    default_workspace_id: str | None
    webhook_secret: str | None
    http_client: Any | None


_lock = threading.Lock()
_cached: FopostSettings | None = None


def _raw() -> dict[str, Any]:
    from django.conf import settings as django_settings

    raw = getattr(django_settings, SETTINGS_NAME, None)
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME} must be a dict, got {type(raw).__name__}."
        )

    unknown = sorted(set(raw) - set(DEFAULTS))
    if unknown:
        known = ", ".join(sorted(DEFAULTS))
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME} has unknown key(s): {', '.join(unknown)}. "
            f"Known keys are: {known}."
        )

    merged = dict(DEFAULTS)
    for key, env_name in ENV_FALLBACKS.items():
        env_value = os.environ.get(env_name)
        if env_value:
            merged[key] = env_value
    merged.update({k: v for k, v in raw.items() if v is not None})
    return merged


def _resolve() -> FopostSettings:
    raw = _raw()

    api_key = raw["API_KEY"]
    if not api_key or not isinstance(api_key, str):
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME}['API_KEY'] is required. Set it, or set the "
            "FOPOST_API_KEY environment variable. Create a key at "
            "https://fopost.com/dashboard/api-keys."
        )

    base_url = raw["BASE_URL"]
    if not isinstance(base_url, str) or not base_url.strip():
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME}['BASE_URL'] must be a non-empty string."
        )

    try:
        timeout = float(raw["TIMEOUT"])
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME}['TIMEOUT'] must be a number of seconds."
        ) from exc
    if timeout <= 0:
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME}['TIMEOUT'] must be greater than zero."
        )

    try:
        max_retries = int(raw["MAX_RETRIES"])
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME}['MAX_RETRIES'] must be an integer."
        ) from exc
    if max_retries < 1:
        raise ImproperlyConfigured(f"settings.{SETTINGS_NAME}['MAX_RETRIES'] must be at least 1.")

    for key in ("DEFAULT_WORKSPACE_ID", "WEBHOOK_SECRET"):
        value = raw[key]
        if value is not None and not isinstance(value, str):
            raise ImproperlyConfigured(
                f"settings.{SETTINGS_NAME}['{key}'] must be a string or None."
            )

    return FopostSettings(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        timeout=timeout,
        max_retries=max_retries,
        default_workspace_id=raw["DEFAULT_WORKSPACE_ID"],
        webhook_secret=raw["WEBHOOK_SECRET"],
        http_client=raw["HTTP_CLIENT"],
    )


def get_settings() -> FopostSettings:
    """The resolved settings, computed once and reused.

    Raises :class:`~django.core.exceptions.ImproperlyConfigured` when the dict
    is missing an API key or carries a value of the wrong shape.
    """
    global _cached
    if _cached is None:
        with _lock:
            if _cached is None:
                _cached = _resolve()
    return _cached


def reset_settings() -> None:
    """Drop the cached settings. Called for you when Django settings change."""
    global _cached
    with _lock:
        _cached = None


@receiver(setting_changed)
def _on_setting_changed(sender: object, setting: str, **kwargs: Any) -> None:
    if setting == SETTINGS_NAME:
        from ._client import reset_client

        reset_settings()
        reset_client()
