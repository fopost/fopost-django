from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

POST_RESPONSE: dict[str, Any] = {
    "id": "post_1",
    "workspace_id": "ws_1",
    "status": "draft",
    "content": [{"id": 1, "text": "Hello from Django", "media": [], "position": 0}],
    "accounts": [{"id": "acc_1", "platform": "twitter", "username": "fopost"}],
}


def run(command: str, *args: str) -> str:
    out = StringIO()
    call_command(command, *args, stdout=out, stderr=StringIO())
    return out.getvalue()


def test_fopost_post_creates_a_draft(stub_api: Any) -> None:
    stub_api.on("POST", "/posts", POST_RESPONSE)

    output = run(
        "fopost_post", "--workspace", "ws_1", "--account", "acc_1", "--text", "Hello from Django"
    )

    body = stub_api.last_json()
    assert body["workspace_id"] == "ws_1"
    assert body["accounts"] == ["acc_1"]
    assert body["content"] == [{"text": "Hello from Django"}]
    assert body["status"] == "draft"
    assert "post_1" in output


def test_fopost_post_uses_the_default_workspace(stub_api: Any) -> None:
    stub_api.on("POST", "/posts", POST_RESPONSE)

    run("fopost_post", "--account", "acc_1", "--text", "Hi")

    assert stub_api.last_json()["workspace_id"] == "ws_default"


def test_fopost_post_schedules(stub_api: Any) -> None:
    stub_api.on("POST", "/posts", {**POST_RESPONSE, "status": "scheduled"})

    run(
        "fopost_post",
        "--account",
        "acc_1",
        "--text",
        "Later",
        "--schedule-at",
        "2026-09-01T10:00:00Z",
    )

    body = stub_api.last_json()
    assert body["status"] == "scheduled"
    assert body["schedule_at"].startswith("2026-09-01T10:00:00")


def test_fopost_post_publishes(stub_api: Any) -> None:
    stub_api.on("POST", "/posts", POST_RESPONSE)
    stub_api.on("POST", "/posts/post_1/publish", {"data": {"queued": True}})

    output = run("fopost_post", "--account", "acc_1", "--text", "Now", "--publish")

    assert stub_api.requests[-1].url.path.endswith("/posts/post_1/publish")
    assert "Queued post post_1" in output


def test_fopost_post_needs_an_account(stub_api: Any) -> None:
    with pytest.raises(CommandError, match="--account"):
        run("fopost_post", "--text", "Nobody to send it to")


def test_fopost_post_refuses_schedule_and_publish(stub_api: Any) -> None:
    with pytest.raises(CommandError, match="mutually exclusive"):
        run(
            "fopost_post",
            "-a",
            "acc_1",
            "-t",
            "x",
            "--schedule-at",
            "2026-09-01T10:00:00Z",
            "--publish",
        )


def test_fopost_post_rejects_an_unparseable_schedule(stub_api: Any) -> None:
    with pytest.raises(CommandError, match="ISO 8601"):
        run("fopost_post", "-a", "acc_1", "-t", "x", "--schedule-at", "next tuesday")


def test_an_api_error_becomes_command_output(stub_api: Any) -> None:
    stub_api.on(
        "POST",
        "/posts",
        {"error": "validation_failed", "message": "content is required"},
        status=422,
    )

    with pytest.raises(CommandError, match="content is required"):
        run("fopost_post", "-a", "acc_1", "-t", "x")


def test_fopost_accounts_lists(stub_api: Any) -> None:
    stub_api.on(
        "GET",
        "/accounts",
        {
            "data": [
                {
                    "id": "acc_1",
                    "platform": "twitter",
                    "username": "fopost",
                    "healthStatus": "healthy",
                }
            ]
        },
    )

    output = run("fopost_accounts", "--workspace", "ws_1")

    assert "acc_1" in output
    assert "twitter" in output
    assert stub_api.requests[-1].url.params["workspaceId"] == "ws_1"


def test_fopost_accounts_json(stub_api: Any) -> None:
    stub_api.on("GET", "/accounts", {"data": [{"id": "acc_1", "platform": "twitter"}]})

    output = run("fopost_accounts", "--json")

    assert '"id": "acc_1"' in output
