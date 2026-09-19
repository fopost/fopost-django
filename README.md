# FoPost for Django

[![PyPI](https://img.shields.io/pypi/v/fopost-django.svg)](https://pypi.org/project/fopost-django/)
[![Python versions](https://img.shields.io/pypi/pyversions/fopost-django.svg)](https://pypi.org/project/fopost-django/)
[![CI](https://github.com/fopost/fopost-django/actions/workflows/ci.yml/badge.svg)](https://github.com/fopost/fopost-django/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Official Django integration for the [FoPost](https://fopost.com) API. Schedule and publish to +30
social platforms from your Django project.

This is a thin wrapper around the [`fopost`](https://github.com/fopost/fopost-python) Python SDK. It
adds Django settings, a lazily-built shared client, two management commands, system checks, and a
signed webhook receiver that fires Django signals. Every platform connection, token refresh, and
delivery happens on the hosted API, so there is nothing to run yourself — and **no models and no
migrations**, because this package stores nothing.

## Requirements

- Python 3.10 or newer
- Django 4.2, 5.0, 5.1, or 5.2
- A FoPost API key from [fopost.com/dashboard/api-keys](https://fopost.com/dashboard/api-keys)

## Install

```bash
pip install fopost-django
```

## Settings

Add the app and one settings dict:

```python
import os

INSTALLED_APPS = [
    # ...
    "fopost_django",
]

FOPOST = {
    "API_KEY": os.environ["FOPOST_API_KEY"],
    "WEBHOOK_SECRET": os.environ["FOPOST_WEBHOOK_SECRET"],
    "DEFAULT_WORKSPACE_ID": os.environ.get("FOPOST_WORKSPACE_ID"),
}
```

| Key | Default | Env fallback | What it does |
| --- | --- | --- | --- |
| `API_KEY` | none, **required** | `FOPOST_API_KEY` | Your API key |
| `BASE_URL` | `https://api.fopost.com/v1` | `FOPOST_BASE_URL` | API root |
| `TIMEOUT` | `30.0` | — | Seconds to wait for one request |
| `MAX_RETRIES` | `3` | — | Attempts for a rate limited request |
| `DEFAULT_WORKSPACE_ID` | `None` | `FOPOST_WORKSPACE_ID` | Workspace the management commands use when `--workspace` is left out |
| `WEBHOOK_SECRET` | `None` | `FOPOST_WEBHOOK_SECRET` | Secret the webhook receiver verifies signatures against |
| `HTTP_CLIENT` | `None` | — | Advanced: an `httpx.Client` to send through, for a proxy or a test transport |

The whole dict is optional as long as `FOPOST_API_KEY` is in the environment. Django refuses to
start without a key — an `ImproperlyConfigured` at boot beats a 401 in a customer's request — and
`manage.py check` warns about the softer misconfigurations (a webhook URL wired up with no secret, a
plaintext base URL, an API key hardcoded into settings).

## Quick start

```python
from django.http import JsonResponse
from fopost_django import client


def announce(request):
    workspace = client.workspaces.list()[0]
    accounts = client.accounts.list(workspace_id=workspace.id)

    post = client.posts.create(
        workspace_id=workspace.id,
        content="Shipping today: scheduled posting straight from Django.",
        accounts=[a.id for a in accounts],
    )
    client.posts.publish(post.id)

    return JsonResponse({"post_id": post.id})
```

`client` is a lazy proxy, so importing it at module scope never touches settings. Prefer an explicit
call? `get_client()` returns the same memoized instance:

```python
from fopost_django import get_client

get_client().posts.list(workspace_id=workspace_id, status="scheduled")
```

The client is built once per process, on first use, behind a lock, and rebuilt automatically if
`settings.FOPOST` changes (which is what `override_settings` does in your tests).

## Management commands

### `fopost_accounts`

```bash
python manage.py fopost_accounts --workspace 9b2f6c1e-...
python manage.py fopost_accounts --json
```

Lists the social accounts connected to a workspace. Falls back to
`FOPOST["DEFAULT_WORKSPACE_ID"]`, and to every workspace the key reaches when neither is set.

### `fopost_post`

```bash
# A draft
python manage.py fopost_post -a acc_1 -a acc_2 --text "Hello from Django"

# Scheduled
python manage.py fopost_post -a acc_1 --text "Later" --schedule-at 2026-09-01T10:00:00Z

# Out the door now
python manage.py fopost_post -a acc_1 --text "Now" --publish
```

| Flag | What it does |
| --- | --- |
| `-w`, `--workspace` | Workspace id. Defaults to `FOPOST["DEFAULT_WORKSPACE_ID"]` |
| `-a`, `--account` | A connected account. Repeat for more than one. At least one is required |
| `-t`, `--text` | The post body. Required |
| `--title` | Title, for platforms that use one |
| `--label` | A label id to attach. Repeat for more than one |
| `--schedule-at` | ISO 8601 datetime. A naive value is read in the project's current timezone |
| `--publish` | Queue the post for delivery straight after creating it |

`--schedule-at` and `--publish` are mutually exclusive. API failures come back as ordinary
`CommandError` output, not a traceback.

## Receiving webhooks

Add the URLs:

```python
from django.urls import include, path

urlpatterns = [
    path("fopost/", include("fopost_django.urls")),
]
```

That serves the receiver at `/fopost/webhook/` (reversible as `reverse("fopost:webhook")`). Register
that URL at [fopost.com/dashboard](https://fopost.com/dashboard), copy the secret it shows you into
`FOPOST["WEBHOOK_SECRET"]`, and connect a receiver:

```python
from django.dispatch import receiver
from fopost_django.signals import post_published, post_failed


@receiver(post_published)
def on_published(sender, event, data, payload, request, delivery_id, **kwargs):
    Article.objects.filter(fopost_post_id=data["postId"]).update(announced=True)


@receiver(post_failed)
def on_failed(sender, data, **kwargs):
    logger.error("FoPost post %s failed", data.get("postId"))
```

Connect them from your app config's `ready()`, the usual way.

| Signal | FoPost event |
| --- | --- |
| `post_published` | `post.published` |
| `post_failed` | `post.failed` |
| `post_partially_failed` | `post.partially_failed` |
| `delivery_published` | `delivery.published` |
| `delivery_failed` | `delivery.failed` |
| `delivery_delayed` | `delivery.delayed` |
| `account_health_changed` | `account.health_changed` |
| `webhook_received` | every verified delivery, whatever the event |

Every receiver gets the same keyword arguments: `event`, `data`, `payload` (the whole envelope, with
its `timestamp`), `request`, and `delivery_id` — the `X-FoPost-Delivery` header, which stays the same
across retries and so makes a good idempotency key.

**How it is verified.** FoPost signs the raw request body with HMAC-SHA256, keyed on the webhook
secret, and sends the hex digest as `X-FoPost-Signature: sha256=<digest>`. The view recomputes it
over `request.body` and compares with `hmac.compare_digest`. A missing, malformed, or wrong
signature is a `403` before any signal fires; a body that is not a JSON object is a `400`. The view
is `csrf_exempt` and accepts `POST` only.

**Failures are meant to propagate.** If a receiver raises, the response is a 5xx and FoPost retries
the delivery with backoff. Keep receivers quick and idempotent, or hand the work to a task queue.

## Testing your own code

Point the SDK at a stub transport instead of the network:

```python
import httpx
from django.test import override_settings
from fopost_django import reset_client


def handler(request):
    return httpx.Response(200, json={"data": {"id": "post_1", "status": "draft"}})


with override_settings(
    FOPOST={
        "API_KEY": "fp_test",
        "HTTP_CLIENT": httpx.Client(transport=httpx.MockTransport(handler)),
    }
):
    reset_client()
    ...
```

`override_settings` already invalidates the cached client; `reset_client()` is there for the cases
where you swap the transport by hand.

## The rest of the API

Posts, accounts, workspaces, labels, AI, media, pagination, error classes and retry behaviour all live in
the parent SDK. See [`fopost` on PyPI](https://pypi.org/project/fopost/) and its
[README](https://github.com/fopost/fopost-python#readme); everything it documents works through
`fopost_django.client` unchanged.

```python
from fopost import FopostError, RateLimitError

try:
    client.posts.publish(post_id)
except RateLimitError as exc:
    retry_in = exc.retry_after
except FopostError as exc:
    print(exc.status, exc.code, exc.message)
```

## Links

- Docs — <https://fopost.com/docs>
- Issues — <https://github.com/fopost/fopost-django/issues>
- Support — <https://fopost.com/contact>

## License

MIT. Copyright (c) 2026 Porter Bridge, LLC.
