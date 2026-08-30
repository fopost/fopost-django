"""The Django app config. Add ``"fopost_django"`` to ``INSTALLED_APPS``."""

from __future__ import annotations

from django.apps import AppConfig

__all__ = ["FopostConfig"]


class FopostConfig(AppConfig):
    name = "fopost_django"
    label = "fopost"
    verbose_name = "FoPost"

    def ready(self) -> None:
        from django.core.checks import register

        from . import conf  # noqa: F401 — connects the setting_changed receiver
        from .checks import check_fopost_settings

        # Fails the boot rather than the first API call, so a missing key shows
        # up in a deploy and not in a customer's request.
        conf.get_settings()

        register(check_fopost_settings)
