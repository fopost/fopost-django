"""Create a post and queue it for delivery, from a standalone script.

export FOPOST_API_KEY=fp_your_key_here
python examples/create_and_publish.py
"""

from __future__ import annotations

import django
from django.conf import settings

settings.configure(
    INSTALLED_APPS=["fopost_django"],
    FOPOST={
        # Left out on purpose: the API key comes from FOPOST_API_KEY.
        "TIMEOUT": 30.0,
    },
    USE_TZ=True,
)
django.setup()

from fopost_django import client  # noqa: E402 — Django has to be set up first


def main() -> None:
    workspaces = client.workspaces.list()
    if not workspaces:
        raise SystemExit("No workspaces on this key. Create one at https://fopost.com/dashboard.")
    workspace = workspaces[0]

    accounts = client.accounts.list(workspace_id=workspace.id)
    if not accounts:
        raise SystemExit(f"No connected accounts in {workspace.name}.")

    post = client.posts.create(
        workspace_id=workspace.id,
        content="Shipping today: scheduled posting straight from Django.",
        accounts=[account.id for account in accounts],
    )
    print(f"Created draft {post.id}")

    client.posts.publish(post.id)
    print(f"Queued {post.id} for delivery to {len(accounts)} account(s)")


if __name__ == "__main__":
    main()
