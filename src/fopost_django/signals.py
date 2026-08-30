"""Django signals fired for each FoPost webhook event.

Every receiver is called with the same keyword arguments::

    @receiver(post_published)
    def on_published(sender, event, data, payload, request, delivery_id, **kwargs):
        ...

``event`` is the FoPost event name, ``data`` its payload body, ``payload`` the
whole envelope (``event``, ``data``, ``timestamp``), and ``delivery_id`` the
value of the ``X-FoPost-Delivery`` header, which is stable across retries and so
makes a good idempotency key.

Receivers run inside the request, and an exception propagates: the view answers
5xx and FoPost redelivers. Keep them quick and idempotent, or hand the work to a
task queue.
"""

from __future__ import annotations

from django.dispatch import Signal

__all__ = [
    "EVENT_SIGNALS",
    "WEBHOOK_EVENTS",
    "account_health_changed",
    "delivery_delayed",
    "delivery_failed",
    "delivery_published",
    "post_failed",
    "post_partially_failed",
    "post_published",
    "webhook_received",
]

#: Fired for every verified webhook, whatever the event.
webhook_received = Signal()

post_published = Signal()
post_failed = Signal()
post_partially_failed = Signal()
delivery_published = Signal()
delivery_failed = Signal()
delivery_delayed = Signal()
account_health_changed = Signal()

#: FoPost event name to the signal it fires.
EVENT_SIGNALS: dict[str, Signal] = {
    "post.published": post_published,
    "post.failed": post_failed,
    "post.partially_failed": post_partially_failed,
    "delivery.published": delivery_published,
    "delivery.failed": delivery_failed,
    "delivery.delayed": delivery_delayed,
    "account.health_changed": account_health_changed,
}

#: The events a webhook can subscribe to, in the order the API lists them.
WEBHOOK_EVENTS: tuple[str, ...] = tuple(EVENT_SIGNALS)
