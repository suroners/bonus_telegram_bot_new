import pytest

from bonus_core.models import Geo, ScraperProxy
from bonus_scraping.services.webshare_service import WebshareProxyClient, WebshareProxySync


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeHttpClient:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, url, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers, "params": params})
        return FakeResponse(self.payload)


def test_webshare_client_uses_token_and_direct_mode():
    http_client = FakeHttpClient({"next": None, "results": []})
    client = WebshareProxyClient(token="test-token", mode="direct", http_client=http_client)

    assert list(client.list_proxies(country_codes=["US"], page_size=10)) == []
    assert http_client.calls == [
        {
            "url": "https://proxy.webshare.io/api/v2/proxy/list/",
            "headers": {"Authorization": "Token test-token"},
            "params": {
                "mode": "direct",
                "page": 1,
                "page_size": 10,
                "country_code__in": "US",
            },
        }
    ]


@pytest.mark.django_db
def test_webshare_sync_imports_valid_proxy_and_maps_geo(settings):
    settings.WEBSHARE_COUNTRY_CODES = []
    Geo.objects.create(code="uk", name="United Kingdom")
    http_client = FakeHttpClient(
        {
            "next": None,
            "results": [
                {
                    "id": "d-10513",
                    "username": "proxy-user",
                    "password": "proxy-pass",
                    "proxy_address": "1.2.3.4",
                    "port": 8168,
                    "valid": True,
                    "country_code": "GB",
                    "city_name": "London",
                }
            ],
        }
    )
    client = WebshareProxyClient(token="test-token", mode="direct", http_client=http_client)

    result = WebshareProxySync(client=client).sync()

    proxy = ScraperProxy.objects.get(name="Webshare d-10513")
    assert result == {"created": 1, "updated": 0, "skipped": 0, "deactivated": 0}
    assert proxy.geo.code == "uk"
    assert proxy.server == "http://1.2.3.4:8168"
    assert proxy.username == "proxy-user"
    assert proxy.password == "proxy-pass"
    assert proxy.is_active is True


@pytest.mark.django_db
def test_webshare_sync_skips_invalid_proxy(settings):
    settings.WEBSHARE_COUNTRY_CODES = []
    http_client = FakeHttpClient(
        {
            "next": None,
            "results": [
                {
                    "id": "d-invalid",
                    "username": "proxy-user",
                    "password": "proxy-pass",
                    "proxy_address": "1.2.3.4",
                    "port": 8168,
                    "valid": False,
                    "country_code": "US",
                    "city_name": "New York",
                }
            ],
        }
    )
    client = WebshareProxyClient(token="test-token", mode="direct", http_client=http_client)

    result = WebshareProxySync(client=client).sync()

    assert result == {"created": 0, "updated": 0, "skipped": 1, "deactivated": 0}
    assert ScraperProxy.objects.count() == 0
