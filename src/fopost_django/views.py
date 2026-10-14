"""The endpoints that receive FoPost webhooks and published blog articles."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from fopost import ArticlePublishedPayload, WebhookVerificationError, webhooks

from .conf import SETTINGS_NAME, get_settings
from .signals import EVENT_SIGNALS, article_published, webhook_received
from .webhooks import DELIVERY_HEADER, EVENT_HEADER, SIGNATURE_HEADER, verify_signature

__all__ = ["FopostWebhookView", "article_webhook"]

logger = logging.getLogger("fopost_django")


@method_decorator(csrf_exempt, name="dispatch")
class FopostWebhookView(View):
    """Verifies the signature, then fires the matching Django signal.

    Answers ``200`` once every receiver has run, ``403`` for a bad or missing
    signature, and ``400`` for a body that is not a JSON object. Subclass and
    override :attr:`secret` to serve more than one webhook from one project.
    """

    http_method_names = ["post"]

    @property
    def secret(self) -> str | None:
        return get_settings().webhook_secret

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        secret = self.secret
        if not secret:
            raise ImproperlyConfigured(
                f"settings.{SETTINGS_NAME}['WEBHOOK_SECRET'] is required to receive webhooks. "
                "It is shown once, when the webhook is created at https://fopost.com/dashboard."
            )

        body = request.body
        if not verify_signature(body, request.headers.get(SIGNATURE_HEADER), secret):
            logger.warning("Rejected a FoPost webhook with a missing or invalid signature.")
            return JsonResponse({"detail": "invalid signature"}, status=403)

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return JsonResponse({"detail": "invalid json"}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "invalid json"}, status=400)

        event = payload.get("event") or request.headers.get(EVENT_HEADER) or ""
        data = payload.get("data")
        kwargs = {
            "event": event,
            "data": data if isinstance(data, dict) else {},
            "payload": payload,
            "request": request,
            "delivery_id": request.headers.get(DELIVERY_HEADER) or None,
        }

        if event == "article.published":
            kwargs["article"] = ArticlePublishedPayload.model_validate(kwargs["data"])

        webhook_received.send(sender=self.__class__, **kwargs)

        signal = EVENT_SIGNALS.get(event)
        if signal is not None:
            signal.send(sender=self.__class__, **kwargs)
        else:
            # A new server-side event should not look like a failure to FoPost.
            logger.info("Received FoPost webhook event %r with no dedicated signal.", event)

        return JsonResponse({"received": True})


@csrf_exempt
@require_POST
def article_webhook(request: HttpRequest) -> HttpResponse:
    """Receive articles the blog Website target publishes to this site.

    Mount it in one line, ``path("fopost/articles/", article_webhook)``, or
    include ``fopost_django.urls``. The parent SDK verifies the signature
    against ``request.body`` and the ``WEBSITE_SECRET`` setting; a forged or
    stale delivery is a ``401``. ``article.test`` answers ``{"ok": true}``.
    ``article.published`` hands the typed article to the
    ``ON_ARTICLE_PUBLISHED`` callable and the ``article_published`` signal.
    Whichever returns a URL string is echoed back as ``{"url": ...}``.
    """
    settings = get_settings()
    if not settings.website_secret:
        raise ImproperlyConfigured(
            f"settings.{SETTINGS_NAME}['WEBSITE_SECRET'] is required to receive articles. "
            "It is shown once, when the Website target is saved in the blog settings."
        )

    try:
        event = webhooks.verify(request.body, request.headers, settings.website_secret)
    except WebhookVerificationError as exc:
        logger.warning("Rejected a FoPost article delivery: %s", exc.code)
        return JsonResponse({"error": exc.code}, status=401)

    if event.event != "article.published":
        return JsonResponse({"ok": True})

    article = ArticlePublishedPayload.model_validate(event.data)
    url: str | None = None
    if settings.on_article_published:
        result = import_string(settings.on_article_published)(article)
        url = result if isinstance(result, str) else None

    responses = article_published.send(
        sender=article_webhook,
        article=article,
        event=event.event,
        data=event.data,
        payload={"event": event.event, "data": event.data, "timestamp": event.timestamp},
        request=request,
        delivery_id=request.headers.get(DELIVERY_HEADER) or None,
    )
    if url is None:
        url = next((r for _, r in responses if isinstance(r, str)), None)

    return JsonResponse({"url": url} if url else {"ok": True})
