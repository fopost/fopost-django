"""The endpoint that receives FoPost webhooks."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .conf import SETTINGS_NAME, get_settings
from .signals import EVENT_SIGNALS, webhook_received
from .webhooks import DELIVERY_HEADER, EVENT_HEADER, SIGNATURE_HEADER, verify_signature

__all__ = ["FopostWebhookView"]

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
                "It is shown once, when the webhook is created at https://app.fopost.com."
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

        webhook_received.send(sender=self.__class__, **kwargs)

        signal = EVENT_SIGNALS.get(event)
        if signal is not None:
            signal.send(sender=self.__class__, **kwargs)
        else:
            # A new server-side event should not look like a failure to FoPost.
            logger.info("Received FoPost webhook event %r with no dedicated signal.", event)

        return JsonResponse({"received": True})
