from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from fopost_django import reset_client

API_PREFIX = "/api/v1"


class StubApi:
    """An offline stand-in for the FoPost API, wired in as the SDK's transport."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Any] = {}
        self.requests: list[httpx.Request] = []

    def on(self, method: str, path: str, body: Any, status: int = 200) -> None:
        self.routes[(method.upper(), path)] = (status, body)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path.startswith(API_PREFIX):
            path = path[len(API_PREFIX) :]
        route = self.routes.get((request.method, path))
        if route is None:
            return httpx.Response(
                404, json={"error": "no_stub", "message": f"no stub for {request.method} {path}"}
            )
        status, body = route
        return httpx.Response(status, json=body)

    def last_json(self) -> Any:
        return json.loads(self.requests[-1].content)


@pytest.fixture
def stub_api(settings: Any) -> Any:
    api = StubApi()
    settings.FOPOST = {
        **settings.FOPOST,
        "HTTP_CLIENT": httpx.Client(transport=httpx.MockTransport(api.handle)),
    }
    reset_client()
    yield api
    reset_client()


@pytest.fixture
def signal_log() -> Any:
    """Record every kwarg set a signal fires with, disconnecting afterwards."""
    connections: list[tuple[Any, Any]] = []

    def listen(signal: Any) -> list[dict[str, Any]]:
        calls: list[dict[str, Any]] = []

        def handler(sender: Any, **kwargs: Any) -> None:
            calls.append(kwargs)

        signal.connect(handler, weak=False)
        connections.append((signal, handler))
        return calls

    yield listen

    for signal, handler in connections:
        signal.disconnect(handler)
