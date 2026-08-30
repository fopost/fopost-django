from __future__ import annotations

from typing import Any

from fopost import Fopost

from fopost_django import client, get_client


def test_get_client_is_memoized(stub_api: Any) -> None:
    assert get_client() is get_client()


def test_settings_reach_the_sdk_client(settings: Any, stub_api: Any) -> None:
    settings.FOPOST = {
        **settings.FOPOST,
        "BASE_URL": "https://api.test.fopost.com/v1/",
        "MAX_RETRIES": 5,
        "TIMEOUT": 12.5,
    }

    built = get_client()

    assert isinstance(built, Fopost)
    assert built.base_url == "https://api.test.fopost.com/v1"
    assert built._http.max_retries == 5
    assert built._http.api_key == "fp_test_key"


def test_a_change_of_settings_rebuilds_the_client(settings: Any, stub_api: Any) -> None:
    first = get_client()
    settings.FOPOST = {**settings.FOPOST, "API_KEY": "fp_rotated"}
    second = get_client()

    assert second is not first
    assert second._http.api_key == "fp_rotated"


def test_the_lazy_proxy_reaches_the_real_client(stub_api: Any) -> None:
    assert client.base_url == get_client().base_url
    assert client.posts is get_client().posts
    assert "lazy" in repr(client)


def test_the_api_key_header_is_sent(stub_api: Any) -> None:
    stub_api.on("GET", "/workspaces", {"data": [{"id": "ws_1", "name": "Acme"}]})

    workspaces = get_client().workspaces.list()

    assert [w.id for w in workspaces] == ["ws_1"]
    assert stub_api.requests[-1].headers["X-API-Key"] == "fp_test_key"
