"""Announce an article on social when an editor publishes it."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import get_object_or_404
from fopost import FopostError

from fopost_django import client

from .models import Article


def announce(request: HttpRequest, slug: str) -> JsonResponse:
    article = get_object_or_404(Article, slug=slug)
    accounts = client.accounts.list(workspace_id=settings.FOPOST["DEFAULT_WORKSPACE_ID"])

    try:
        post = client.posts.create(
            workspace_id=settings.FOPOST["DEFAULT_WORKSPACE_ID"],
            content=[
                f"New on the blog: {article.title}",
                {"text": article.url, "media": []},
            ],
            accounts=[a.id for a in accounts if a.platform in {"twitter", "linkedin", "bluesky"}],
        )
        client.posts.publish(post.id)
    except FopostError as exc:
        return JsonResponse({"error": exc.code, "detail": exc.message}, status=502)

    article.fopost_post_id = post.id
    article.save(update_fields=["fopost_post_id"])
    return JsonResponse({"post_id": post.id, "status": post.status})
