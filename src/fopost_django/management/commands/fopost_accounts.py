"""``manage.py fopost_accounts`` — list the social accounts a workspace has connected."""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import CommandParser

from .._base import FopostCommand


class Command(FopostCommand):
    help = "List the social accounts connected to a FoPost workspace."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-w",
            "--workspace",
            dest="workspace",
            help="Workspace id. Defaults to FOPOST['DEFAULT_WORKSPACE_ID'].",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Print raw JSON instead of a table.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        client = self.client()
        workspace_id = options["workspace"] or None
        accounts = self.call(client.accounts.list, workspace_id=workspace_id)

        if options["as_json"]:
            self.stdout.write(json.dumps([a.model_dump(mode="json") for a in accounts], indent=2))
            return

        if not accounts:
            self.stdout.write(self.style.WARNING("No connected accounts."))
            return

        rows = [
            (a.id, a.platform, a.username or a.name or "", a.health_status or "") for a in accounts
        ]
        headers = ("ID", "PLATFORM", "USERNAME", "HEALTH")
        widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]

        self.stdout.write("  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)))
        for row in rows:
            self.stdout.write("  ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)))
        self.stdout.write(self.style.SUCCESS(f"\n{len(rows)} account(s)."))
