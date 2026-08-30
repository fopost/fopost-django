"""System checks, so ``manage.py check`` catches a half-configured install.

The app config already refuses to start without an API key, so these cover the
settings that only bite later: a webhook route wired up with no secret, a
plaintext base URL, or a workspace default that no command can use.
"""

from __future__ import annotations

from typing import Any

from django.core.checks import CheckMessage, Warning

from .conf import SETTINGS_NAME, get_settings

__all__ = ["check_fopost_settings"]

WEBHOOK_SECRET_ID = "fopost_django.W001"
INSECURE_BASE_URL_ID = "fopost_django.W002"
API_KEY_IN_SETTINGS_ID = "fopost_django.W003"


def _webhook_url_is_wired() -> bool:
    from django.urls import NoReverseMatch, reverse

    try:
        reverse("fopost:webhook")
    except NoReverseMatch:
        return False
    except Exception:  # URLConf not loadable yet — nothing useful to say.
        return False
    return True


def check_fopost_settings(app_configs: Any = None, **kwargs: Any) -> list[CheckMessage]:
    from django.conf import settings as django_settings

    messages: list[CheckMessage] = []
    settings = get_settings()

    if not settings.webhook_secret and _webhook_url_is_wired():
        messages.append(
            Warning(
                "fopost_django.urls is included but no webhook secret is set.",
                hint=(
                    f"Set {SETTINGS_NAME}['WEBHOOK_SECRET'] (or FOPOST_WEBHOOK_SECRET) to the "
                    "secret shown when you created the webhook. Until then every delivery is "
                    "rejected."
                ),
                id=WEBHOOK_SECRET_ID,
            )
        )

    if settings.base_url.startswith("http://") and not settings.base_url.startswith(
        ("http://localhost", "http://127.0.0.1")
    ):
        messages.append(
            Warning(
                f"{SETTINGS_NAME}['BASE_URL'] is plain HTTP, so your API key travels in the clear.",
                hint="Use an https:// URL outside local development.",
                id=INSECURE_BASE_URL_ID,
            )
        )

    raw = getattr(django_settings, SETTINGS_NAME, {})
    if isinstance(raw, dict) and isinstance(raw.get("API_KEY"), str) and raw["API_KEY"]:
        messages.append(
            Warning(
                f"{SETTINGS_NAME}['API_KEY'] is set to a literal value.",
                hint=(
                    "Read it from the environment instead — os.environ['FOPOST_API_KEY'] — so the "
                    "key never lands in version control."
                ),
                id=API_KEY_IN_SETTINGS_ID,
            )
        )

    return messages
