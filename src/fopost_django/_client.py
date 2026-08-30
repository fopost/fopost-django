"""The lazily-built, process-wide :class:`fopost.Fopost` client."""

from __future__ import annotations

import threading
from typing import Any

from fopost import Fopost

from .conf import get_settings

__all__ = ["LazyClient", "get_client", "reset_client"]

_lock = threading.Lock()
_client: Fopost | None = None


def get_client() -> Fopost:
    """The configured API client, built on first use and reused afterwards.

    Safe to call from any thread; the first caller builds it and the rest wait.
    """
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                settings = get_settings()
                _client = Fopost(
                    api_key=settings.api_key,
                    base_url=settings.base_url,
                    timeout=settings.timeout,
                    max_retries=settings.max_retries,
                    http_client=settings.http_client,
                )
    return _client


def reset_client() -> None:
    """Discard the cached client so the next call rebuilds it from settings."""
    global _client
    with _lock:
        stale, _client = _client, None
    if stale is not None:
        stale.close()


class LazyClient:
    """Attribute proxy so ``from fopost_django import client`` works at import time.

    Every attribute read resolves through :func:`get_client`, so importing this
    module never touches settings and a settings change is picked up at once.
    """

    __slots__ = ()

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return getattr(get_client(), name)

    def __dir__(self) -> list[str]:
        return dir(get_client())

    def __repr__(self) -> str:
        return "<fopost_django.client (lazy)>"
