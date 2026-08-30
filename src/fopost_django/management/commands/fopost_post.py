"""``manage.py fopost_post`` — create a post, optionally scheduling or publishing it."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.management.base import CommandError, CommandParser
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .._base import FopostCommand


class Command(FopostCommand):
    help = (
        "Create a FoPost post. Without --schedule-at or --publish it stays a draft; "
        "--publish queues it for delivery straight away."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "-w",
            "--workspace",
            dest="workspace",
            help="Workspace id. Defaults to FOPOST['DEFAULT_WORKSPACE_ID'].",
        )
        parser.add_argument(
            "-a",
            "--account",
            dest="accounts",
            action="append",
            default=[],
            metavar="ACCOUNT_ID",
            help="A connected account to post to. Repeat for more than one.",
        )
        parser.add_argument("-t", "--text", dest="text", required=True, help="The post body.")
        parser.add_argument("--title", dest="title", help="Title, for platforms that use one.")
        parser.add_argument(
            "--label",
            dest="labels",
            action="append",
            default=[],
            metavar="LABEL_ID",
            help="A label to attach. Repeat for more than one.",
        )
        parser.add_argument(
            "--schedule-at",
            dest="schedule_at",
            metavar="ISO8601",
            help="When to publish, e.g. 2026-09-01T10:00:00Z. Implies --status scheduled.",
        )
        parser.add_argument(
            "--publish",
            action="store_true",
            dest="publish",
            help="Queue the post for immediate delivery after creating it.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        accounts: list[str] = options["accounts"]
        if not accounts:
            raise CommandError("At least one --account is required.")
        if options["schedule_at"] and options["publish"]:
            raise CommandError("--schedule-at and --publish are mutually exclusive.")

        workspace_id = self.workspace_id(options["workspace"])
        schedule_at = _parse_when(options["schedule_at"])
        client = self.client()

        post = self.call(
            client.posts.create,
            workspace_id=workspace_id,
            content=options["text"],
            accounts=accounts,
            status="scheduled" if schedule_at else "draft",
            schedule_at=schedule_at,
            title=options["title"],
            labels=options["labels"] or None,
        )

        if options["publish"]:
            self.call(client.posts.publish, post.id)
            self.stdout.write(self.style.SUCCESS(f"Queued post {post.id} for delivery."))
            return

        when = f" for {schedule_at.isoformat()}" if schedule_at else ""
        self.stdout.write(self.style.SUCCESS(f"Created {post.status} post {post.id}{when}."))


def _parse_when(raw: str | None) -> datetime | None:
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is None:
        raise CommandError(f"--schedule-at is not an ISO 8601 datetime: {raw!r}")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed
