from django.urls import include, path

urlpatterns = [
    path("fopost/", include("fopost_django.urls")),
]
