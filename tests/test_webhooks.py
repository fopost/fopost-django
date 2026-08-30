from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client
from django.urls import reverse

from fopost_django.signals import post_failed, post_published, webhook_received
from fopost_django.webhooks import compute_signature, verify_signature

SECRET = "whsec_test"


def envelope(event: str = "post.published") -> bytes:
    return json.dumps(
        {
            "event": event,
            "data": {"postId": "post_1", "status": "published"},
            "timestamp": "2026-08-30T10:00:00.000Z",
        }
    ).encode()


def deliver(
    http: Client, body: bytes, *, signature: str | None = None, event: str = "post.published"
) -> Any:
    headers: dict[str, str] = {"X-FoPost-Event": event, "X-FoPost-Delivery": "wh_42"}
    if signature is not None:
        headers["X-FoPost-Signature"] = signature
    return http.post(
        reverse("fopost:webhook"), data=body, content_type="application/json", headers=headers
    )


def test_signature_roundtrip() -> None:
    body = b'{"event":"post.published"}'
    assert verify_signature(body, compute_signature(body, SECRET), SECRET)
    assert compute_signature(body, SECRET).startswith("sha256=")


def test_a_bare_hex_signature_is_accepted() -> None:
    body = b"{}"
    bare = compute_signature(body, SECRET).removeprefix("sha256=")
    assert verify_signature(body, bare, SECRET)


@pytest.mark.parametrize("header", [None, "", "sha256=deadbeef", "not-a-signature"])
def test_a_bad_signature_is_rejected(client: Client, header: str | None) -> None:
    response = deliver(client, envelope(), signature=header)

    assert response.status_code == 403
    assert response.json() == {"detail": "invalid signature"}


def test_a_tampered_body_is_rejected(client: Client) -> None:
    body = envelope()
    response = deliver(
        client, b'{"event":"post.failed"}', signature=compute_signature(body, SECRET)
    )

    assert response.status_code == 403


def test_a_good_delivery_fires_the_signal(client: Client, signal_log: Any) -> None:
    calls = signal_log(post_published)
    body = envelope()

    response = deliver(client, body, signature=compute_signature(body, SECRET))

    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert len(calls) == 1
    assert calls[0]["event"] == "post.published"
    assert calls[0]["data"]["postId"] == "post_1"
    assert calls[0]["delivery_id"] == "wh_42"
    assert calls[0]["payload"]["timestamp"] == "2026-08-30T10:00:00.000Z"


def test_only_the_matching_signal_fires(client: Client, signal_log: Any) -> None:
    published = signal_log(post_published)
    failed = signal_log(post_failed)
    every = signal_log(webhook_received)
    body = envelope("post.failed")

    deliver(client, body, signature=compute_signature(body, SECRET), event="post.failed")

    assert len(failed) == 1
    assert len(every) == 1
    assert published == []


def test_an_unknown_event_is_still_accepted(client: Client, signal_log: Any) -> None:
    every = signal_log(webhook_received)
    body = envelope("something.new")

    response = deliver(client, body, signature=compute_signature(body, SECRET))

    assert response.status_code == 200
    assert every[0]["event"] == "something.new"


@pytest.mark.parametrize("body", [b"not json", b'"a string"', b"[]"])
def test_a_non_object_body_is_a_400(client: Client, body: bytes) -> None:
    response = deliver(client, body, signature=compute_signature(body, SECRET))

    assert response.status_code == 400


def test_a_get_is_not_allowed(client: Client) -> None:
    assert client.get(reverse("fopost:webhook")).status_code == 405


def test_no_secret_is_a_configuration_error(client: Client, settings: Any) -> None:
    settings.FOPOST = {**settings.FOPOST, "WEBHOOK_SECRET": None}
    body = envelope()

    with pytest.raises(ImproperlyConfigured, match="WEBHOOK_SECRET"):
        deliver(client, body, signature=compute_signature(body, SECRET))
