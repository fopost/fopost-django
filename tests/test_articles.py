from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import Client
from django.urls import reverse
from fopost import ArticlePublishedPayload

from fopost_django.signals import article_published

SECRET = "whsec_site"

ARTICLE = {
    "id": "art_1",
    "title": "Trail shoes",
    "slug": "trail-shoes",
    "excerpt": None,
    "bodyMarkdown": "# Trail shoes",
    "bodyHtml": "<h1>Trail shoes</h1>",
    "featuredImage": None,
    "images": [],
    "tags": ["shoes"],
    "keyword": "trail shoes",
    "wordCount": 2,
    "publishedAt": "2026-10-11T10:00:00.000Z",
    "publishedUrl": None,
}

received: list[ArticlePublishedPayload] = []


def store_article(article: ArticlePublishedPayload) -> str:
    received.append(article)
    return f"https://yourbrand.com/blog/{article.slug}"


def envelope(event: str = "article.published") -> bytes:
    data = ARTICLE if event == "article.published" else {}
    return json.dumps(
        {"event": event, "data": data, "timestamp": "2026-10-11T10:00:00.000Z"}
    ).encode()


def sign(body: bytes, secret: str = SECRET, *, at: int | None = None) -> dict[str, str]:
    ts = str(at if at is not None else int(time.time()))
    digest = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return {"X-FoPost-Timestamp": ts, "X-FoPost-Signature-256": f"sha256={digest}"}


def deliver(http: Client, body: bytes, headers: dict[str, str], event: str) -> Any:
    return http.post(
        reverse("fopost:articles"),
        data=body,
        content_type="application/json",
        headers={"X-FoPost-Event": event, "X-FoPost-Delivery": "wh_7", **headers},
    )


@pytest.fixture(autouse=True)
def website_settings(settings: Any) -> None:
    settings.FOPOST = {**settings.FOPOST, "WEBSITE_SECRET": SECRET}
    received.clear()


def test_a_signed_test_delivery_is_accepted(client: Client) -> None:
    body = envelope("article.test")

    response = deliver(client, body, sign(body), "article.test")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_a_tampered_body_is_a_401(client: Client) -> None:
    body = envelope()

    response = deliver(client, body + b" ", sign(body), "article.published")

    assert response.status_code == 401
    assert response.json() == {"error": "invalid_signature"}
    assert received == []


def test_a_stale_delivery_is_a_401(client: Client) -> None:
    body = envelope()

    response = deliver(client, body, sign(body, at=int(time.time()) - 600), "article.published")

    assert response.status_code == 401
    assert response.json() == {"error": "stale_delivery"}


def test_a_published_article_reaches_the_callback(client: Client, settings: Any) -> None:
    settings.FOPOST = {
        **settings.FOPOST,
        "ON_ARTICLE_PUBLISHED": "tests.test_articles.store_article",
    }
    body = envelope()

    response = deliver(client, body, sign(body), "article.published")

    assert response.status_code == 200
    assert response.json() == {"url": "https://yourbrand.com/blog/trail-shoes"}
    assert len(received) == 1
    assert received[0].slug == "trail-shoes"
    assert received[0].body_html == "<h1>Trail shoes</h1>"


def test_a_published_article_reaches_the_signal(client: Client, signal_log: Any) -> None:
    calls = signal_log(article_published)
    body = envelope()

    response = deliver(client, body, sign(body), "article.published")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(calls) == 1
    assert calls[0]["article"].title == "Trail shoes"
    assert calls[0]["data"]["slug"] == "trail-shoes"
    assert calls[0]["delivery_id"] == "wh_7"


def test_no_website_secret_is_a_configuration_error(client: Client, settings: Any) -> None:
    settings.FOPOST = {**settings.FOPOST, "WEBSITE_SECRET": None}
    body = envelope()

    with pytest.raises(ImproperlyConfigured, match="WEBSITE_SECRET"):
        deliver(client, body, sign(body), "article.published")
