"""URLs to include in your project::

    path("fopost/", include("fopost_django.urls"))

which serves the webhook receiver at ``/fopost/webhook/``, reversible as
``reverse("fopost:webhook")``.
"""

from __future__ import annotations

from django.urls import path

from .views import FopostWebhookView

app_name = "fopost"

urlpatterns = [
    path("webhook/", FopostWebhookView.as_view(), name="webhook"),
]
