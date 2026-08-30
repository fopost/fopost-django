# Examples

## `create_and_publish.py`

A standalone script — no project needed. It configures Django in-process, creates a post in the
first workspace your key can reach, and queues it for delivery.

```bash
pip install fopost-django
export FOPOST_API_KEY=fp_your_key_here
python examples/create_and_publish.py
```

## `blog/`

Fragments from a realistic Django app: `receivers.py` reacts to FoPost webhooks, `views.py`
announces a newly published article. Copy them into an app of your own — they are not runnable on
their own.
