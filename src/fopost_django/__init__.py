"""fopost-django — the official Django integration for the FoPost API.

Add ``"fopost_django"`` to ``INSTALLED_APPS``, put your key in settings::

    FOPOST = {"API_KEY": os.environ["FOPOST_API_KEY"]}

and reach the API from anywhere::

    from fopost_django import client

    client.posts.create(workspace_id=..., content="Hello from Django", accounts=[...])

Everything past that point is the ``fopost`` package: this one only wires it
into Django settings, management commands, system checks, and signals.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from ._client import LazyClient, get_client, reset_client
from .conf import FopostSettings, get_settings, reset_settings

try:
    __version__ = _pkg_version("fopost-django")
except PackageNotFoundError:  # running from a source tree
    __version__ = "0.0.0"

#: Import-time-safe proxy for :func:`get_client`. Every attribute read resolves
#: through the real client, so this is safe at module scope.
client = LazyClient()

__all__ = [
    "FopostSettings",
    "LazyClient",
    "__version__",
    "client",
    "get_client",
    "get_settings",
    "reset_client",
    "reset_settings",
]
