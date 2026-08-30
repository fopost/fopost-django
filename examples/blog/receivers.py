"""React to FoPost webhooks.

Import this module from your app config's ``ready()`` so the receivers connect::

    class BlogConfig(AppConfig):
        name = "blog"

        def ready(self):
            from . import receivers  # noqa: F401
"""

from __future__ import annotations

import logging

from django.dispatch import receiver

from fopost_django.signals import account_health_changed, post_failed, post_published

logger = logging.getLogger(__name__)


@receiver(post_published)
def mark_article_announced(sender, event, data, delivery_id, **kwargs):
    """A post reached every account it was aimed at."""
    from .models import Article

    Article.objects.filter(fopost_post_id=data["postId"]).update(announced=True)
    logger.info("FoPost delivery %s announced post %s", delivery_id, data["postId"])


@receiver(post_failed)
def alert_on_failure(sender, event, data, **kwargs):
    logger.error("FoPost post %s failed to publish: %s", data.get("postId"), data)


@receiver(account_health_changed)
def note_account_trouble(sender, data, **kwargs):
    if data.get("healthStatus") != "healthy":
        logger.warning("FoPost account %s needs reconnecting", data.get("accountId"))
