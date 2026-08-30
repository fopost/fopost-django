"""Verifying the signature FoPost puts on a webhook delivery.

FoPost signs the raw request body with HMAC-SHA256 keyed on the webhook's
secret, hex-encodes it, and sends it as::

    X-FoPost-Signature: sha256=<hex digest>
    X-FoPost-Event: post.published
    X-FoPost-Delivery: <delivery id, stable across retries>

The digest covers the bytes on the wire, so it must be checked against
``request.body`` and never against a re-serialised copy of the parsed JSON.
"""

from __future__ import annotations

import hashlib
import hmac

__all__ = [
    "DELIVERY_HEADER",
    "EVENT_HEADER",
    "SIGNATURE_HEADER",
    "SIGNATURE_PREFIX",
    "compute_signature",
    "verify_signature",
]

SIGNATURE_HEADER = "X-FoPost-Signature"
EVENT_HEADER = "X-FoPost-Event"
DELIVERY_HEADER = "X-FoPost-Delivery"
SIGNATURE_PREFIX = "sha256="


def compute_signature(body: bytes, secret: str) -> str:
    """The value FoPost sends in ``X-FoPost-Signature`` for this body."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return SIGNATURE_PREFIX + digest


def verify_signature(body: bytes, header: str | None, secret: str | None) -> bool:
    """Constant-time check of a received signature header against the body."""
    if not header or not secret:
        return False
    received = header.strip()
    if received.startswith(SIGNATURE_PREFIX):
        received = received[len(SIGNATURE_PREFIX) :]
    expected = compute_signature(body, secret)[len(SIGNATURE_PREFIX) :]
    return hmac.compare_digest(expected, received.lower())
