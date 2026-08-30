"""Shared plumbing for the FoPost management commands."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from fopost import Fopost, FopostError

from .._client import get_client
from ..conf import get_settings

__all__ = ["FopostCommand"]


class FopostCommand(BaseCommand):
    """A command that talks to the API, turning SDK failures into CommandError."""

    def client(self) -> Fopost:
        try:
            return get_client()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

    def workspace_id(self, given: str | None) -> str:
        workspace = given or get_settings().default_workspace_id
        if not workspace:
            raise CommandError(
                "No workspace. Pass --workspace, or set FOPOST['DEFAULT_WORKSPACE_ID']."
            )
        return workspace

    def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """Run an SDK call, reporting an API error as clean command output."""
        try:
            return func(*args, **kwargs)
        except FopostError as exc:
            raise CommandError(f"FoPost API error: {exc}") from exc
