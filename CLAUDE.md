# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What This Is

`fopost-django` on PyPI (import package `fopost_django`) — the official Django integration for the
FoPost API. It is a **thin wrapper** around the `fopost` package on PyPI (sibling repo
`fopost-python`). It owns Django wiring and nothing else: settings, a memoized client, management
commands, system checks, and a signed webhook receiver that fires Django signals.

**Never reimplement here what the parent already does.** HTTP, auth headers, retries, the `{"data":
...}` envelope, pagination, response models, and the error hierarchy all live in `fopost`. If you
find yourself writing `httpx` or parsing an API response in this repo, the change belongs upstream.

There are **no models and no migrations**. This package stores nothing.

## Brand Rules

- The product is **FoPost** (`fopost.com`). Never write "OwlStack" — retired Aug 2026.
- Never write an email address. Support is https://fopost.com/contact and GitHub issues.
- Never name AI providers/models, infrastructure vendors, or any person.

## Architecture

```
src/fopost_django/
  __init__.py                     re-exports get_client, get_settings, and the `client` proxy
  conf.py                         reads settings.FOPOST, applies defaults + env fallbacks, validates
  _client.py                      get_client() / reset_client() / LazyClient
  apps.py                         FopostConfig — validates at boot, registers the checks
  checks.py                       django.core.checks warnings
  signals.py                      one Signal per webhook event + EVENT_SIGNALS map
  webhooks.py                     HMAC-SHA256 signature computation and verification
  views.py                        FopostWebhookView (csrf_exempt, POST only)
  urls.py                         app_name = "fopost", the webhook route
  management/_base.py             FopostCommand — client access, workspace default, error mapping
  management/commands/fopost_post.py
  management/commands/fopost_accounts.py
```

How a call flows: `client.posts.create(...)` → `LazyClient.__getattr__` → `get_client()` →
(first call only) `get_settings()` → `fopost.Fopost(...)` → the parent SDK's transport.

How a webhook flows: `POST /fopost/webhook/` → `FopostWebhookView.post` → `verify_signature` against
`request.body` → `webhook_received.send(...)` → the event's own signal.

`conf.py` and `_client.py` each cache behind a `threading.Lock`, and a `setting_changed` receiver in
`conf.py` clears both when `settings.FOPOST` changes — which is what makes `override_settings` work
in a user's tests.

## API Contract

Owned by the parent SDK; repeated here only where this repo has to agree with it.

- Base URL `https://api.fopost.com/v1`, auth header `X-API-Key` (not Bearer)
- Error envelope `{"error": "<code>", "message": "<text>"}`; 3 attempts, backoff, honouring
  `Retry-After` on 429
- `FOPOST["BASE_URL"]`, `TIMEOUT`, and `MAX_RETRIES` are passed straight through to
  `fopost.Fopost(...)` — do not reinterpret them

### Webhook signature (confirmed against the API source)

The API signs deliveries in `apps/api/src/services/webhook-dispatcher.ts` (`signPayload`) and sends
them in `apps/api/src/workers/webhook.worker.ts`:

- `X-FoPost-Signature: sha256=<hex HMAC-SHA256 of the raw body, keyed on the webhook secret>`
- `X-FoPost-Event: <event name>`
- `X-FoPost-Delivery: <delivery id, stable across the 5 retries>`
- Body: `{"event": ..., "data": {...}, "timestamp": "<ISO 8601>"}`

Verify over `request.body`, never over a re-serialised parse — a reordered key changes the digest.
Compare with `hmac.compare_digest`. The subscribable events are `WEBHOOK_EVENTS` in
`apps/api/src/handlers/webhooks.ts`; keep `signals.EVENT_SIGNALS` in step with that list.

## Commands

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                      # offline, stubs the SDK transport via FOPOST["HTTP_CLIENT"]
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/pip install "django==4.2.*" # spot-check the floor before a release
```

Tests run with `pytest-django` against `tests/settings.py`. The suite never touches the network: the
`stub_api` fixture injects an `httpx.MockTransport` through `FOPOST["HTTP_CLIENT"]`, which is a real
supported setting rather than a monkeypatch.

## Parent dependency

`fopost` is published on PyPI, so `pip install -e ".[dev]"` resolves it normally and CI needs no
from-source shim. The pin is `fopost>=0.1,<1.0`.

Note the floor: the parent requires **Python >= 3.10**, so this package does too. A 3.9 classifier
would advertise an install that cannot resolve.

## Conventions

- Type hints everywhere, `from __future__ import annotations` at the top of every module, `py.typed`
  shipped in the wheel
- Ruff, line length 100, rules `E,F,I,UP,B,DJ`. Run `ruff format` before committing
- Short comments, only for a non-obvious "why". Public symbols get a docstring
- Settings validation raises `ImproperlyConfigured` with a message that says what to set and where
- New settings key → add it to `DEFAULTS` in `conf.py`, the `FopostSettings` dataclass, the README
  table, and a validation branch. Unknown keys are rejected on purpose, so a typo fails loudly

## Releasing

Tag `v<version>` matching `pyproject.toml`; `.github/workflows/release.yml` builds with
`python -m build` and publishes to PyPI.

**No API token secret.** Publishing uses PyPI **trusted publishing** (OIDC), so the workflow needs
`permissions: id-token: write` and nothing else. Before the first tag, set it up once on PyPI:

1. Sign in at <https://pypi.org>, open **Your projects → fopost-django → Manage → Publishing** (for a
   name that does not exist yet, use **Your account → Publishing → Add a pending publisher**)
2. Add a **GitHub** publisher with owner `fopost`, repository `fopost-django`, workflow filename
   `release.yml`, environment name `pypi`
3. In GitHub, create the `pypi` environment under **Settings → Environments** and add whatever
   reviewers you want gating a release

The workflow refuses to publish when the tag and `pyproject.toml` version disagree, and smoke-tests
the built wheel in a clean virtualenv first.

## Git

Conventional Commits, atomic. Branch `feature/<description>`, merge to `main` via PR.
Never `gh pr create` — push the branch and hand over the compare link.
