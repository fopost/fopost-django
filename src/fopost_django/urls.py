"""URLs to include in your project::

    path("fopost/", include("fopost_django.urls"))

which serves the webhook receiver at ``/fopost/webhook/``, reversible as
``reverse("fopost:webhook")``, and the blog article receiver at
``/fopost/articles/`` (``reverse("fopost:articles")``).
"""

from __future__ import annotations

from django.urls import path

from .views import FopostWebhookView, article_webhook

app_name = "fopost"

urlpatterns = [
    path("webhook/", FopostWebhookView.as_view(), name="webhook"),
    path("articles/", article_webhook, name="articles"),
]
